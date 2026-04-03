"""
Celery tasks for async backtest execution.
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "prism",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True, name="backtest.run")
def run_backtest_task(self, request: dict):
    """Async Celery task: fetch data, run backtest, return enriched result dict."""
    import asyncio
    from app.core.data_layer import fetch_ohlcv
    from app.core.backtest_engine import BacktestEngine
    from app.core.strategy import load_strategy

    self.update_state(state="STARTED", meta={"progress": 0})

    symbol = request.get("symbol", "KRW-BTC")
    interval = request.get("interval", "1d")
    strategy_id = request.get("strategy_id", "")
    initial_capital = float(request.get("initial_capital", 10_000_000))
    params = request.get("params", {})

    try:
        # 1. Fetch market data
        bars = asyncio.get_event_loop().run_until_complete(
            fetch_ohlcv(symbol=symbol, interval=interval, limit=365)
        )
        self.update_state(state="PROGRESS", meta={"progress": 30, "bars_fetched": len(bars)})

        # 2. Load strategy
        strategy = load_strategy(strategy_id, params)

        # 3. Run backtest engine
        engine = BacktestEngine(initial_capital=initial_capital)
        result = engine.run(strategy=strategy, ohlcv=bars, symbol=symbol)
        self.update_state(state="PROGRESS", meta={"progress": 80})

        # 4. Serialize trades for JSON transport
        trades_data = [
            {
                "timestamp": t.timestamp,
                "symbol": t.symbol,
                "action": t.action,
                "price": t.price,
                "size": t.size,
                "commission": t.commission,
                "slippage": t.slippage,
            }
            for t in result.trades
        ]

        return {
            "strategy_name": result.strategy_name,
            "strategy_id": strategy_id,
            "symbol": result.symbol,
            "start": result.start,
            "end": result.end,
            "initial_capital": result.initial_capital,
            "final_equity": result.final_equity,
            "total_return": result.total_return,
            "total_trades": result.total_trades,
            "trades": trades_data,
            "equity_curve": result.equity_curve,
        }

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
