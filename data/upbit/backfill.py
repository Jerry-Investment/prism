"""Historical data backfill — fetches full candle history from Upbit."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

from config import settings
from data.db import async_conn
from .client import UpbitClient
from .collector import write_candles

INTERVAL_UNIT: dict[str, tuple[str, int | None]] = {
    # interval_key -> (endpoint_type, minute_unit)
    "1":   ("minute", 1),
    "3":   ("minute", 3),
    "5":   ("minute", 5),
    "15":  ("minute", 15),
    "60":  ("minute", 60),
    "240": ("minute", 240),
    "D":   ("day", None),
    "W":   ("week", None),
}

# How many candles fit in one API call
MAX_PER_CALL = 200


async def _get_existing_range(market: str, interval: str) -> tuple[datetime | None, datetime | None]:
    async with async_conn() as conn:
        row = await conn.fetchrow(
            "SELECT MIN(time) AS oldest, MAX(time) AS newest FROM candles "
            "WHERE market = $1 AND interval = $2",
            market, interval,
        )
    if row:
        return row["oldest"], row["newest"]
    return None, None


async def backfill_market_interval(
    client: UpbitClient,
    market: str,
    interval: str,
    from_time: datetime,
    to_time: datetime,
) -> int:
    """Backfill candles for one (market, interval) pair in [from_time, to_time].

    Returns total rows written.
    """
    ep_type, minute_unit = INTERVAL_UNIT.get(interval, ("minute", 1))

    # Track a backfill job
    async with async_conn() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO backfill_jobs (market, interval, from_time, to_time, status)
            VALUES ($1, $2, $3, $4, 'running')
            RETURNING id
            """,
            market, interval, from_time, to_time,
        )

    cursor_time = to_time
    total_written = 0

    try:
        while cursor_time > from_time:
            if ep_type == "minute":
                candles = await client.get_minute_candles(
                    market, unit=minute_unit, count=MAX_PER_CALL, to=cursor_time
                )
            elif ep_type == "day":
                candles = await client.get_day_candles(market, count=MAX_PER_CALL, to=cursor_time)
            else:  # week
                candles = await client.get_week_candles(market, count=MAX_PER_CALL, to=cursor_time)

            if not candles:
                break

            # Filter to desired range
            in_range = [
                c for c in candles
                if c.candle_date_time_utc.replace(tzinfo=timezone.utc) >= from_time
            ]
            n = await write_candles(in_range, interval)
            total_written += n

            oldest_in_batch = min(
                c.candle_date_time_utc.replace(tzinfo=timezone.utc) for c in candles
            )
            if oldest_in_batch <= from_time or len(candles) < MAX_PER_CALL:
                break

            cursor_time = oldest_in_batch - timedelta(seconds=1)
            logger.debug(f"backfill {market}/{interval}: cursor={cursor_time} written={total_written}")

            # Small sleep to respect rate limits
            await asyncio.sleep(0.15)

        async with async_conn() as conn:
            await conn.execute(
                "UPDATE backfill_jobs SET status='done', rows_written=$1, updated_at=NOW() WHERE id=$2",
                total_written, job_id,
            )
        logger.info(f"Backfill complete: {market}/{interval} rows={total_written}")

    except Exception as e:
        async with async_conn() as conn:
            await conn.execute(
                "UPDATE backfill_jobs SET status='failed', error=$1, updated_at=NOW() WHERE id=$2",
                str(e), job_id,
            )
        logger.error(f"Backfill failed: {market}/{interval}: {e}")
        raise

    return total_written


async def run_backfill(
    markets: list[str] | None = None,
    intervals: list[str] | None = None,
    days: int | None = None,
    concurrency: int = 3,
) -> None:
    """Run full historical backfill for all markets × intervals.

    Args:
        markets: Markets to backfill (defaults to settings.default_markets).
        intervals: Candle intervals to backfill (defaults to settings.candle_intervals).
        days: How many days back to fetch (defaults to settings.backfill_days).
        concurrency: Max parallel (market, interval) tasks.
    """
    markets = markets or settings.default_markets
    intervals = intervals or settings.candle_intervals
    days = days or settings.backfill_days

    to_time = datetime.now(tz=timezone.utc)
    from_time = to_time - timedelta(days=days)

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(market: str, interval: str) -> None:
        async with sem:
            await backfill_market_interval(client, market, interval, from_time, to_time)

    async with UpbitClient() as client:
        tasks = [
            asyncio.create_task(_bounded(m, i), name=f"backfill:{m}:{i}")
            for m in markets
            for i in intervals
        ]
        logger.info(f"Starting backfill: {len(tasks)} tasks, from={from_time} to={to_time}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error(f"Backfill finished with {len(errors)} error(s)")
    else:
        logger.info("Backfill completed successfully")
