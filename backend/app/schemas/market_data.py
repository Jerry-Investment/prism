from pydantic import BaseModel
from typing import Optional


class OHLCVBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataQuery(BaseModel):
    symbol: str
    interval: str = "1d"
    limit: int = 200
    to: Optional[str] = None
