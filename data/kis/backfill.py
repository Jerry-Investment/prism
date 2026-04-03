"""Historical backfill for Korean stocks (KOSPI 200 daily candles).

Fetches full daily OHLCV history and writes it to stock_candles.
KIS returns max 100 candles per call, so we paginate backwards.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from loguru import logger

from config import settings
from data.db import async_conn
from .client import KISClient, MAX_DAILY_PER_CALL
from .collector import write_stock_candles, sync_kospi200_constituents

KST = timezone(timedelta(hours=9))


async def _get_existing_range(ticker: str) -> tuple[date | None, date | None]:
    async with async_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT MIN(time)::date AS oldest, MAX(time)::date AS newest
            FROM stock_candles
            WHERE ticker = $1 AND interval = 'D'
            """,
            ticker,
        )
    if row and row["oldest"]:
        return row["oldest"], row["newest"]
    return None, None


async def backfill_ticker(
    client: KISClient,
    ticker: str,
    market_div: Literal["J", "Q"],
    from_date: date,
    to_date: date,
) -> int:
    """Backfill daily candles for one ticker in [from_date, to_date].

    KIS `inquire-daily-itemchartprice` returns max 100 candles per call.
    We paginate by adjusting `end_date` backwards until we cover `from_date`.

    Returns total rows written.
    """
    async with async_conn() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO stock_backfill_jobs
                (ticker, interval, from_time, to_time, status)
            VALUES ($1, $2, $3, $4, 'running')
            RETURNING id
            """,
            ticker, "D",
            datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc),
            datetime(to_date.year, to_date.month, to_date.day, tzinfo=timezone.utc),
        )

    cursor_end = to_date
    total_written = 0

    try:
        while cursor_end >= from_date:
            candles = await client.get_daily_candles(
                ticker, from_date, cursor_end, market_div=market_div
            )
            if not candles:
                break

            n = await write_stock_candles(candles)
            total_written += n

            # Find oldest candle in this batch
            oldest_time = min(c.time for c in candles)
            oldest_date = oldest_time.date()

            if oldest_date <= from_date or len(candles) < MAX_DAILY_PER_CALL:
                break

            # Move cursor back one day before the oldest we received
            cursor_end = oldest_date - timedelta(days=1)
            logger.debug(f"backfill {ticker}/D: cursor={cursor_end} written={total_written}")

            await asyncio.sleep(0.1)   # be polite to the API

        async with async_conn() as conn:
            await conn.execute(
                """
                UPDATE stock_backfill_jobs
                SET status='done', rows_written=$1, updated_at=NOW()
                WHERE id=$2
                """,
                total_written, job_id,
            )
        logger.info(f"Backfill done: {ticker}/D rows={total_written}")

    except Exception as e:
        async with async_conn() as conn:
            await conn.execute(
                """
                UPDATE stock_backfill_jobs
                SET status='failed', error=$1, updated_at=NOW()
                WHERE id=$2
                """,
                str(e), job_id,
            )
        logger.error(f"Backfill failed: {ticker}/D: {e}")
        raise

    return total_written


async def run_stock_backfill(
    tickers: list[dict] | None = None,
    days: int | None = None,
    concurrency: int = 5,
) -> None:
    """Backfill KOSPI 200 daily candles.

    Args:
        tickers: [{"ticker": "005930", "market_div": "J"}, …]
                 Defaults to fetching the current KOSPI 200 list from KIS.
        days:    How many calendar days back to fetch (default: settings.stock_backfill_days).
        concurrency: Max parallel ticker tasks.
    """
    days = days or settings.stock_backfill_days
    to_date = datetime.now(tz=KST).date()
    from_date = to_date - timedelta(days=days)

    async with KISClient() as client:
        if tickers is None:
            tickers = await sync_kospi200_constituents(client)
            if not tickers:
                logger.error("No tickers resolved for backfill — aborting")
                return

        logger.info(
            f"Starting KOSPI 200 daily backfill: "
            f"{len(tickers)} tickers, {from_date} → {to_date}"
        )

        sem = asyncio.Semaphore(concurrency)

        async def _bounded(t: dict) -> None:
            async with sem:
                await backfill_ticker(
                    client,
                    t["ticker"],
                    t.get("market_div", "J"),
                    from_date,
                    to_date,
                )

        tasks = [
            asyncio.create_task(_bounded(t), name=f"backfill:{t['ticker']}")
            for t in tickers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error(f"Stock backfill finished with {len(errors)} error(s)")
    else:
        logger.info(f"Stock backfill complete — {len(tickers)} tickers")
