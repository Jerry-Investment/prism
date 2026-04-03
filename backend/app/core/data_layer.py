"""
Data Layer — Phase 1: Upbit REST API integration.
DEX will build the full pipeline on top of this foundation.
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
