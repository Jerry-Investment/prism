#!/usr/bin/env python3
"""Start the real-time data collector."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from data.db import apply_schema
from data.upbit.collector import DataCollector


async def main():
    logger.info("Applying DB schema...")
    await apply_schema()
    collector = DataCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
