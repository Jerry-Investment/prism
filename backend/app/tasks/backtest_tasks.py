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
    """
    Async Celery task: fetch data, run backtest, return result dict.
    Full implementation in Phase 2 — currently returns a stub.
    """
    import asyncio
    from app.core.data_layer import fetch_ohlcv

    self.update_state(state="STARTED", meta={"progress": 0})

    symbol = request.get("symbol", "KRW-BTC")
    interval = request.get("interval", "1d")
    limit = 200

    try:
        # Fetch market data
        bars = asyncio.get_event_loop().run_until_complete(
            fetch_ohlcv(symbol=symbol, interval=interval, limit=limit)
        )
        self.update_state(state="PROGRESS", meta={"progress": 50, "bars_fetched": len(bars)})

        # Placeholder result — ARIA will wire in real strategy logic
        result = {
            "strategy_id": request.get("strategy_id"),
            "symbol": symbol,
            "bars": len(bars),
            "status": "completed (stub)",
        }

        return result

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
