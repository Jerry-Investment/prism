#!/usr/bin/env python3
"""Run historical data backfill.

Usage:
    python scripts/run_backfill.py                         # all markets, 365 days
    python scripts/run_backfill.py --markets KRW-BTC --days 90
    python scripts/run_backfill.py --intervals 1 60 D
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from data.db import apply_schema
from data.upbit.backfill import run_backfill


async def main():
    parser = argparse.ArgumentParser(description="PRISM historical data backfill")
    parser.add_argument("--markets", nargs="+", help="Markets to backfill (e.g. KRW-BTC KRW-ETH)")
    parser.add_argument("--intervals", nargs="+", help="Candle intervals (e.g. 1 60 D)")
    parser.add_argument("--days", type=int, default=None, help="Days of history to fetch")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel tasks")
    args = parser.parse_args()

    logger.info("Applying DB schema...")
    await apply_schema()

    await run_backfill(
        markets=args.markets,
        intervals=args.intervals,
        days=args.days,
        concurrency=args.concurrency,
    )


if __name__ == "__main__":
    asyncio.run(main())
