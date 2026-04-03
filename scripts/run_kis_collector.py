#!/usr/bin/env python3
"""Start the KIS (국내주식) real-time data collector.

Requires KIS_APP_KEY and KIS_APP_SECRET to be set in .env.
Polls KOSPI 200 minute candles during market hours (09:00-15:30 KST).

Usage:
    python scripts/run_kis_collector.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from config import settings
from data.db import apply_schema
from data.kis.collector import StockDataCollector


async def main():
    if not settings.kis_app_key or not settings.kis_app_secret:
        logger.error(
            "KIS credentials not configured. "
            "Set KIS_APP_KEY and KIS_APP_SECRET in .env"
        )
        sys.exit(1)

    logger.info("Applying DB schema...")
    await apply_schema()

    collector = StockDataCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
