from fastapi import APIRouter, Query
from app.schemas.market_data import OHLCVBar, MarketDataQuery

router = APIRouter()


@router.get("/ohlcv", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str = Query(..., description="e.g. KRW-BTC"),
    interval: str = Query("1d", description="1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(200, ge=1, le=1000),
):
    """Fetch OHLCV candles for a symbol. Data source: Upbit (Phase 1)."""
    from app.core.data_layer import fetch_ohlcv
    bars = await fetch_ohlcv(symbol=symbol, interval=interval, limit=limit)
    return bars


@router.get("/symbols")
async def list_symbols():
    """List available trading symbols."""
    return {
        "upbit": ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-ADA"],
        "kis": [],  # Phase 2
    }
