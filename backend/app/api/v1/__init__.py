from fastapi import APIRouter

from app.api.v1 import backtest, strategy, market_data

router = APIRouter()
router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
router.include_router(strategy.router, prefix="/strategies", tags=["strategies"])
router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
