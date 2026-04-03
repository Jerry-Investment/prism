"""KIS real-time data collection — polls minute candles during market hours.

Korean market hours: 09:00 ~ 15:30 KST (UTC+9)
Pre-market (시간외): 08:00 ~ 09:00, Post-market: 15:30 ~ 18:00
We only collect during regular session (09:00 ~ 15:30 KST).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Literal

from loguru import logger

from config import settings
from data.db import async_conn
from .client import KISClient
from .models import StockCandle

KST = timezone(timedelta(hours=9))
MARKET_OPEN = (9, 0)    # 09:00 KST
MARKET_CLOSE = (15, 30)  # 15:30 KST


# ─── Market hours guard ───────────────────────────────────────────────────────

def is_market_open() -> bool:
    """True if current KST time is within regular session."""
    now_kst = datetime.now(tz=KST)
    # Monday=0 … Friday=4; skip weekends
    if now_kst.weekday() >= 5:
        return False
    t = (now_kst.hour, now_kst.minute)
    return MARKET_OPEN <= t < MARKET_CLOSE


def seconds_until_market_open() -> float:
    """Seconds until next 09:00 KST open (skipping weekends)."""
    now_kst = datetime.now(tz=KST)
    # Next open = today if before 09:00, else tomorrow
    candidate = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
    if now_kst >= candidate:
        candidate = candidate + timedelta(days=1)
    # Skip to Monday if candidate lands on weekend
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return (candidate - now_kst).total_seconds()


# ─── DB writers ───────────────────────────────────────────────────────────────

async def write_stock_candles(candles: list[StockCandle]) -> int:
    if not candles:
        return 0
    rows = [
        (
            c.time,
            c.ticker,
            c.market_div,
            c.interval,
            c.open,
            c.high,
            c.low,
            c.close,
            c.volume,
            c.trade_value,
        )
        for c in candles
    ]
    async with async_conn() as conn:
        await conn.executemany(
            """
            INSERT INTO stock_candles
                (time, ticker, market_div, interval, open, high, low, close,
                 volume, trade_value)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (time, ticker, interval) DO UPDATE
                SET open=EXCLUDED.open, high=EXCLUDED.high,
                    low=EXCLUDED.low, close=EXCLUDED.close,
                    volume=EXCLUDED.volume, trade_value=EXCLUDED.trade_value
            """,
            rows,
        )
    return len(rows)


# ─── Polling tasks ────────────────────────────────────────────────────────────

async def poll_minute_candles(
    client: KISClient,
    ticker: str,
    market_div: Literal["J", "Q"],
    poll_seconds: int = 60,
) -> None:
    """Continuously poll 1-minute candles for a single ticker during market hours."""
    while True:
        if not is_market_open():
            wait = seconds_until_market_open()
            logger.info(f"Market closed — sleeping {wait:.0f}s until next open")
            await asyncio.sleep(min(wait, 3600))  # re-check hourly at most
            continue

        try:
            candles = await client.get_minute_candles(
                ticker, interval_minutes=1, market_div=market_div
            )
            if candles:
                n = await write_stock_candles(candles)
                logger.debug(f"candles upserted: ticker={ticker} interval=1 n={n}")
        except Exception as e:
            logger.error(f"poll_minute_candles error [{ticker}]: {e}")

        await asyncio.sleep(poll_seconds)


async def sync_kospi200_constituents(client: KISClient) -> list[dict]:
    """Fetch and upsert KOSPI 200 constituent list, return list of tickers."""
    try:
        stocks = await client.get_kospi200_tickers()
    except Exception as e:
        logger.error(f"Failed to fetch KOSPI 200 constituents: {e}")
        return []

    if not stocks:
        logger.warning("KOSPI 200 list returned empty — skipping upsert")
        return []

    today = datetime.now(tz=KST).date()
    rows = [
        (s.ticker, s.name, s.sector, s.market_div, today)
        for s in stocks
    ]
    async with async_conn() as conn:
        await conn.executemany(
            """
            INSERT INTO kospi200_constituents (ticker, name, sector, market_div, added_date)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (ticker, added_date) DO UPDATE
                SET name=EXCLUDED.name, sector=EXCLUDED.sector
            """,
            rows,
        )
    logger.info(f"KOSPI 200 constituents synced — {len(stocks)} stocks")
    return [{"ticker": s.ticker, "market_div": s.market_div} for s in stocks]


# ─── Collector orchestrator ───────────────────────────────────────────────────

class StockDataCollector:
    """Orchestrates real-time minute-candle polling for KOSPI stocks."""

    # Poll 1-minute candles every 60 seconds
    CANDLE_POLL_SECONDS = 60

    def __init__(
        self,
        tickers: list[dict] | None = None,   # [{"ticker": "005930", "market_div": "J"}]
    ):
        self.tickers = tickers   # None = fetch from API at startup

    async def run(self) -> None:
        async with KISClient() as client:
            # Resolve ticker list
            if self.tickers is None:
                self.tickers = await sync_kospi200_constituents(client)
                if not self.tickers:
                    logger.error("No tickers to collect — aborting")
                    return

            logger.info(f"StockDataCollector starting — {len(self.tickers)} tickers")

            tasks = [
                asyncio.create_task(
                    poll_minute_candles(
                        client,
                        t["ticker"],
                        t.get("market_div", "J"),
                        self.CANDLE_POLL_SECONDS,
                    ),
                    name=f"candles:{t['ticker']}",
                )
                for t in self.tickers
            ]

            logger.info(f"Launched {len(tasks)} polling tasks")
            await asyncio.gather(*tasks)
