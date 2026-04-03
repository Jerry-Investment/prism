from fastapi import APIRouter

from app.api.v1 import analytics, auth, backtest, strategy, market_data

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(strategy.router, prefix="/strategies", tags=["strategies"])
router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
