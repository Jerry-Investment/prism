"""
Celery tasks for async backtest execution.
"""

import sys
import os

# Make prism importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

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

# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY = {
    "ma_cross": ("prism.strategy.examples.ma_cross", "MACrossStrategy"),
    "rsi":      ("prism.strategy.examples.rsi",      "RSIStrategy"),
    "volume":   ("prism.strategy.examples.volume",   "VolumeStrategy"),
}


def _load_strategy_class(strategy_id: str):
    """Import and return the strategy class for the given strategy_id key."""
    if strategy_id not in STRATEGY_REGISTRY:
        valid = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(
            f"Unknown strategy_id '{strategy_id}'. Valid options: {valid}"
        )
    module_path, class_name = STRATEGY_REGISTRY[strategy_id]
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="backtest.run")
def run_backtest_task(self, request: dict):
    """
    Async Celery task: fetch data, run backtest, return serialised result dict.
    """
    import asyncio
    import dataclasses
    import pandas as pd

    self.update_state(state="STARTED", meta={"progress": 0})

    # ---- 1. Resolve strategy ------------------------------------------------
    strategy_id = request.get("strategy_id", "")
    try:
        StrategyClass = _load_strategy_class(strategy_id)
    except ValueError as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

    params = request.get("params", {})
    strategy = StrategyClass(params=params)

    # ---- 2. Fetch data ------------------------------------------------------
    symbol   = request.get("symbol", "KRW-BTC")
    start    = request.get("start", "2024-01-01")
    end      = request.get("end", "2024-12-31")
    interval = request.get("interval", "1d")

    from app.core.data_layer import fetch_ohlcv_range

    try:
        loop = asyncio.new_event_loop()
        try:
            bars = loop.run_until_complete(
                fetch_ohlcv_range(symbol=symbol, start=start, end=end, interval=interval)
            )
        finally:
            loop.close()
    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": f"Data fetch failed: {exc}"})
        raise

    if len(bars) < 2:
        msg = (
            f"Insufficient data: only {len(bars)} bar(s) returned for "
            f"{symbol} [{start} → {end}] at interval {interval}. "
            "Need at least 2 bars to run a backtest."
        )
        self.update_state(state="FAILURE", meta={"error": msg})
        raise ValueError(msg)

    self.update_state(state="PROGRESS", meta={"progress": 25, "bars_fetched": len(bars)})

    # ---- 3. Build DataFrame with UTC DatetimeIndex -------------------------
    records = [
        {
            "timestamp": pd.Timestamp(b.timestamp, tz="UTC"),
            "open":   b.open,
            "high":   b.high,
            "low":    b.low,
            "close":  b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    df = pd.DataFrame(records).set_index("timestamp").sort_index()
    data = {symbol: df}

    # ---- 4. Run backtest with progress reporting ---------------------------
    from app.core.backtest_engine import BacktestEngine

    initial_capital = request.get("initial_capital", 10_000_000)
    engine = BacktestEngine(initial_capital=initial_capital)

    def progress_cb(pct: float) -> None:
        # pct from engine is 50–100; report as-is
        self.update_state(
            state="PROGRESS",
            meta={"progress": int(pct), "bars_fetched": len(bars)},
        )

    try:
        result = engine.run(strategy, data, progress_cb=progress_cb)
    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": f"Backtest failed: {exc}"})
        raise

    # ---- 5. Serialize result -----------------------------------------------
    def _serialise_result(r) -> dict:
        d = dataclasses.asdict(r)
        # Ensure benchmarks list is present (list of dicts via asdict)
        return d

    serialised = _serialise_result(result)

    self.update_state(state="PROGRESS", meta={"progress": 100})
    return serialised
