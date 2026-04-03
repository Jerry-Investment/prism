"""Data collection pipeline — polls Upbit and writes to TimescaleDB."""
import asyncio
from datetime import datetime, timezone
from loguru import logger

from config import settings
from data.db import async_conn
from .client import UpbitClient
from .models import Candle, Orderbook, Trade

# ─── Writers ──────────────────────────────────────────────────────────────────

async def write_candles(candles: list[Candle], interval: str) -> int:
    if not candles:
        return 0
    rows = [
        (
            c.candle_date_time_utc.replace(tzinfo=timezone.utc),
            c.market,
            interval,
            c.opening_price,
            c.high_price,
            c.low_price,
            c.trade_price,
            c.candle_acc_trade_volume,
            c.candle_acc_trade_price,
        )
        for c in candles
    ]
    async with async_conn() as conn:
        await conn.executemany(
            """
            INSERT INTO candles
                (time, market, interval, open, high, low, close, volume, quote_volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (time, market, interval) DO UPDATE
                SET open=EXCLUDED.open, high=EXCLUDED.high,
                    low=EXCLUDED.low, close=EXCLUDED.close,
                    volume=EXCLUDED.volume, quote_volume=EXCLUDED.quote_volume
            """,
            rows,
        )
    return len(rows)


async def write_orderbook(ob: Orderbook) -> None:
    ts = datetime.fromtimestamp(ob.timestamp / 1000, tz=timezone.utc)
    async with async_conn() as conn:
        await conn.execute(
            """
            INSERT INTO orderbook_snapshots (time, market, total_ask_size, total_bid_size)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
            """,
            ts, ob.market, ob.total_ask_size, ob.total_bid_size,
        )
        ask_bid_rows = []
        for u in ob.orderbook_units:
            ask_bid_rows.append((ts, ob.market, "ask", u.ask_price, u.ask_size))
            ask_bid_rows.append((ts, ob.market, "bid", u.bid_price, u.bid_size))
        await conn.executemany(
            """
            INSERT INTO orderbook_units (time, market, side, price, size)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO NOTHING
            """,
            ask_bid_rows,
        )


async def write_trades(trades: list[Trade]) -> int:
    if not trades:
        return 0
    rows = [
        (
            datetime.fromtimestamp(t.timestamp / 1000, tz=timezone.utc),
            t.market,
            str(t.sequential_id),
            t.trade_price,
            t.trade_volume,
            t.ask_bid,
            t.prev_closing_price,
            t.change_price,
        )
        for t in trades
    ]
    async with async_conn() as conn:
        await conn.executemany(
            """
            INSERT INTO trades
                (time, market, trade_id, price, volume, side,
                 prev_closing_price, change_price)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (time, market, trade_id) DO NOTHING
            """,
            rows,
        )
    return len(rows)


# ─── Polling tasks ────────────────────────────────────────────────────────────

async def poll_candles(client: UpbitClient, market: str, interval: str, poll_seconds: int) -> None:
    """Continuously poll candle data for a market/interval pair."""
    unit_map = {"1": 1, "3": 3, "5": 5, "15": 15, "60": 60, "240": 240}
    while True:
        try:
            if interval in unit_map:
                candles = await client.get_minute_candles(market, unit=unit_map[interval], count=5)
            elif interval == "D":
                candles = await client.get_day_candles(market, count=2)
            elif interval == "W":
                candles = await client.get_week_candles(market, count=2)
            else:
                logger.warning(f"Unknown interval {interval}")
                await asyncio.sleep(poll_seconds)
                continue

            n = await write_candles(candles, interval)
            logger.debug(f"candles upserted: market={market} interval={interval} n={n}")
        except Exception as e:
            logger.error(f"poll_candles error [{market}/{interval}]: {e}")

        await asyncio.sleep(poll_seconds)


async def poll_orderbook(client: UpbitClient, markets: list[str], poll_seconds: float = 1.0) -> None:
    """Continuously poll order book snapshots."""
    while True:
        try:
            obs = await client.get_orderbook(markets)
            for ob in obs:
                await write_orderbook(ob)
            logger.debug(f"orderbook updated for {len(obs)} markets")
        except Exception as e:
            logger.error(f"poll_orderbook error: {e}")
        await asyncio.sleep(poll_seconds)


async def poll_trades(client: UpbitClient, markets: list[str], poll_seconds: float = 2.0) -> None:
    """Continuously poll recent trades."""
    while True:
        try:
            for market in markets:
                trades = await client.get_trades(market, count=100)
                n = await write_trades(trades)
                logger.debug(f"trades written: market={market} n={n}")
        except Exception as e:
            logger.error(f"poll_trades error: {e}")
        await asyncio.sleep(poll_seconds)


# ─── Collector orchestrator ───────────────────────────────────────────────────

class DataCollector:
    """Launches and supervises all polling coroutines."""

    # Poll intervals in seconds per candle interval
    CANDLE_POLL_SECONDS: dict[str, int] = {
        "1": 60, "3": 60, "5": 60, "15": 60,
        "60": 300, "240": 900, "D": 3600, "W": 14400,
    }

    def __init__(self, markets: list[str] | None = None, candle_intervals: list[str] | None = None):
        self.markets = markets or settings.default_markets
        self.candle_intervals = candle_intervals or settings.candle_intervals

    async def run(self) -> None:
        logger.info(f"DataCollector starting — markets={self.markets}")
        async with UpbitClient() as client:
            tasks = []

            # Candle polling — one task per (market × interval)
            for market in self.markets:
                for interval in self.candle_intervals:
                    poll_secs = self.CANDLE_POLL_SECONDS.get(interval, 60)
                    tasks.append(
                        asyncio.create_task(
                            poll_candles(client, market, interval, poll_secs),
                            name=f"candles:{market}:{interval}",
                        )
                    )

            # Order book — batched per 10 markets
            batch_size = 10
            for i in range(0, len(self.markets), batch_size):
                batch = self.markets[i : i + batch_size]
                tasks.append(
                    asyncio.create_task(poll_orderbook(client, batch), name=f"orderbook:batch{i}")
                )

            # Trades
            tasks.append(asyncio.create_task(poll_trades(client, self.markets), name="trades"))

            logger.info(f"Launched {len(tasks)} polling tasks")
            await asyncio.gather(*tasks)
