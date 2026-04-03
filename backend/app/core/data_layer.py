"""
Data Layer — Phase 1: Upbit REST API integration.
Phase 2 adds fetch_ohlcv_range for date-range paginated fetching.
"""

import httpx
from typing import Optional
from app.schemas.market_data import OHLCVBar

UPBIT_REST_BASE = "https://api.upbit.com/v1"

_INTERVAL_MAP = {
    "1m": ("minutes", 1),
    "3m": ("minutes", 3),
    "5m": ("minutes", 5),
    "15m": ("minutes", 15),
    "30m": ("minutes", 30),
    "1h": ("minutes", 60),
    "4h": ("minutes", 240),
    "1d": ("days", None),
    "1w": ("weeks", None),
}


async def fetch_ohlcv(
    symbol: str,
    interval: str = "1d",
    limit: int = 200,
    to: Optional[str] = None,
) -> list[OHLCVBar]:
    """Fetch OHLCV bars from Upbit public API."""
    if interval not in _INTERVAL_MAP:
        raise ValueError(f"Unsupported interval: {interval}")

    unit_type, unit_value = _INTERVAL_MAP[interval]

    if unit_type == "minutes":
        url = f"{UPBIT_REST_BASE}/candles/minutes/{unit_value}"
    elif unit_type == "days":
        url = f"{UPBIT_REST_BASE}/candles/days"
    else:
        url = f"{UPBIT_REST_BASE}/candles/weeks"

    params: dict = {"market": symbol, "count": min(limit, 200)}
    if to:
        params["to"] = to

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    bars = []
    for candle in reversed(data):
        bars.append(
            OHLCVBar(
                timestamp=candle["candle_date_time_utc"],
                open=candle["opening_price"],
                high=candle["high_price"],
                low=candle["low_price"],
                close=candle["trade_price"],
                volume=candle["candle_acc_trade_volume"],
            )
        )
    return bars


async def fetch_ohlcv_range(
    symbol: str,
    start: str,   # ISO date "2024-01-01"
    end: str,     # ISO date "2024-12-31"
    interval: str = "1d",
) -> list[OHLCVBar]:
    """
    Fetch all OHLCV bars for *symbol* between *start* and *end* (inclusive).

    Paginates through Upbit 200-bars-at-a-time using the ``to`` cursor param,
    walking backwards from *end* until we have covered the full range.
    Returns bars sorted ascending by timestamp.
    """
    from datetime import datetime, timezone, timedelta

    if interval not in _INTERVAL_MAP:
        raise ValueError(f"Unsupported interval: {interval}")

    unit_type, unit_value = _INTERVAL_MAP[interval]

    if unit_type == "minutes":
        url = f"{UPBIT_REST_BASE}/candles/minutes/{unit_value}"
    elif unit_type == "days":
        url = f"{UPBIT_REST_BASE}/candles/days"
    else:
        url = f"{UPBIT_REST_BASE}/candles/weeks"

    # Parse boundary datetimes (assume UTC midnight when no time given)
    def _parse_dt(s: str) -> datetime:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        raise ValueError(f"Cannot parse datetime: {s!r}")

    start_dt = _parse_dt(start)
    end_dt = _parse_dt(end)
    # Include the full end day for daily intervals
    if "T" not in end:
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

    # Cursor starts just after end boundary and walks backwards
    cursor_dt = end_dt + timedelta(seconds=1)

    all_bars: list[OHLCVBar] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            to_str = cursor_dt.strftime("%Y-%m-%dT%H:%M:%S")
            params: dict = {"market": symbol, "count": 200, "to": to_str}

            response = await client.get(url, params=params)
            response.raise_for_status()
            page_data = response.json()

            if not page_data:
                break

            page_bars: list[OHLCVBar] = []
            for candle in page_data:
                ts_str = candle["candle_date_time_utc"]
                bar = OHLCVBar(
                    timestamp=ts_str,
                    open=candle["opening_price"],
                    high=candle["high_price"],
                    low=candle["low_price"],
                    close=candle["trade_price"],
                    volume=candle["candle_acc_trade_volume"],
                )
                page_bars.append(bar)

            # page_data is returned newest-first; find the oldest bar in this page
            # candle_date_time_utc format: "2024-06-01T00:00:00"
            oldest_ts_str = page_data[-1]["candle_date_time_utc"]
            oldest_dt = _parse_dt(oldest_ts_str)

            all_bars.extend(page_bars)

            # Stop if the oldest bar in this page is already before start
            if oldest_dt <= start_dt:
                break

            # Move cursor to just before the oldest bar in this page
            cursor_dt = oldest_dt - timedelta(seconds=1)

    # Sort ascending
    all_bars.sort(key=lambda b: b.timestamp)

    # Filter to the requested range
    filtered = [
        b for b in all_bars
        if _parse_dt(b.timestamp) >= start_dt and _parse_dt(b.timestamp) <= end_dt
    ]

    return filtered
