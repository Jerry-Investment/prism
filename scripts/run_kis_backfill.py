#!/usr/bin/env python3
"""Run historical KOSPI 200 daily candle backfill via KIS API.

Requires KIS_APP_KEY and KIS_APP_SECRET to be set in .env.

Usage:
    python scripts/run_kis_backfill.py                  # KOSPI 200, 2 years
    python scripts/run_kis_backfill.py --days 365       # 1 year
    python scripts/run_kis_backfill.py --tickers 005930 000660  # specific tickers
    python scripts/run_kis_backfill.py --concurrency 3
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from config import settings
from data.db import apply_schema
from data.kis.backfill import run_stock_backfill


async def main():
    parser = argparse.ArgumentParser(description="PRISM KIS historical stock backfill")
    parser.add_argument(
        "--tickers", nargs="+",
        help="Stock tickers to backfill (e.g. 005930 000660). "
             "Defaults to full KOSPI 200 list fetched from KIS."
    )
    parser.add_argument("--days", type=int, default=None, help="Days of history to fetch")
    parser.add_argument("--concurrency", type=int, default=5, help="Parallel tasks")
    args = parser.parse_args()

    if not settings.kis_app_key or not settings.kis_app_secret:
        logger.error(
            "KIS credentials not configured. "
            "Set KIS_APP_KEY and KIS_APP_SECRET in .env"
        )
        sys.exit(1)

    logger.info("Applying DB schema...")
    await apply_schema()

    tickers = None
    if args.tickers:
        tickers = [{"ticker": t, "market_div": "J"} for t in args.tickers]

    await run_stock_backfill(
        tickers=tickers,
        days=args.days,
        concurrency=args.concurrency,
    )


if __name__ == "__main__":
    asyncio.run(main())
