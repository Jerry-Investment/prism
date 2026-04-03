"""
PRISM Analytics Engine — bridges BacktestResult with the risk/metrics calculator.

Adds monthly/yearly return aggregation on top of the core MetricsCalculator
defined in risk/metrics.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

# Allow importing risk module from project root (4 levels up from backend/app/core/)
_root = Path(__file__).resolve().parents[4]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from risk.metrics import MetricsCalculator, CombinedMetrics  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _equity_to_returns(equity_curve: list[dict]) -> list[float]:
    equities = [e["equity"] for e in equity_curve]
    if len(equities) < 2:
        return []
    return [
        (equities[i] - equities[i - 1]) / equities[i - 1]
        for i in range(1, len(equities))
    ]


def _trade_pnl_from_list(trades: list[dict]) -> list[float]:
    """Derive per-trade P&L by matching sequential buy/sell pairs."""
    buys = [t for t in trades if t.get("action") == "buy"]
    sells = [t for t in trades if t.get("action") == "sell"]
    pnl: list[float] = []
    for b, s in zip(buys, sells):
        pnl.append((s["price"] - b["price"]) * b["size"])
    return pnl


def _monthly_returns(equity_curve: list[dict]) -> dict[str, float]:
    """Return {YYYY-MM: return} from equity curve."""
    if not equity_curve:
        return {}
    df = pd.DataFrame(equity_curve)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    monthly = df["equity"].resample("ME").last()
    monthly_prev = monthly.shift(1)
    monthly_ret = (monthly - monthly_prev) / monthly_prev
    return {
        str(k)[:7]: round(float(v), 6)
        for k, v in monthly_ret.items()
        if not (math.isnan(float(v)) if isinstance(v, float) else pd.isna(v))
    }


def _yearly_returns(equity_curve: list[dict]) -> dict[str, float]:
    """Return {YYYY: return} from equity curve."""
    if not equity_curve:
        return {}
    df = pd.DataFrame(equity_curve)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    yearly = df["equity"].resample("YE").last()
    yearly_prev = yearly.shift(1)
    yearly_ret = (yearly - yearly_prev) / yearly_prev
    return {
        str(k)[:4]: round(float(v), 6)
        for k, v in yearly_ret.items()
        if not (math.isnan(float(v)) if isinstance(v, float) else pd.isna(v))
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_analytics(
    equity_curve: list[dict],
    trades: list[dict] | None = None,
    periods_per_year: int = 365,
    risk_free_rate: float = 0.03,
) -> dict[str, Any]:
    """Compute full analytics from equity curve and trade list.

    Parameters
    ----------
    equity_curve:
        List of {"timestamp": str, "equity": float}.
    trades:
        Optional list of trade dicts with "action", "price", "size" keys.
    periods_per_year:
        365 for crypto (24h), 252 for equities.
    risk_free_rate:
        Annual risk-free rate as decimal (default 0.03 = 3%).

    Returns
    -------
    dict with keys: performance, risk, monthly_returns, yearly_returns.
    """
    returns = _equity_to_returns(equity_curve)
    trade_pnl = _trade_pnl_from_list(trades) if trades else None

    calc = MetricsCalculator(
        returns=returns,
        trades=trade_pnl,
        periods_per_year=periods_per_year,
        risk_free_rate=risk_free_rate,
    )
    combined: CombinedMetrics = calc.compute_all()
    perf = combined.performance
    risk = combined.risk

    sortino = perf.sortino_ratio
    sortino_out = None if sortino == float("inf") else round(sortino, 4)

    return {
        "performance": {
            "sharpe_ratio": round(perf.sharpe_ratio, 4),
            "sortino_ratio": sortino_out,
            "max_drawdown": round(perf.max_drawdown, 6),
            "max_drawdown_duration": perf.max_drawdown_duration,
            "win_rate": round(perf.win_rate, 4),
            "profit_factor": round(perf.profit_factor, 4),
            "total_return": round(perf.total_return, 6),
            "annualised_return": round(perf.annualised_return, 6),
            "annualised_volatility": round(perf.annualised_volatility, 6),
            "calmar_ratio": round(perf.calmar_ratio, 4),
        },
        "risk": {
            "var_95": round(risk.var_95, 6),
            "var_99": round(risk.var_99, 6),
            "cvar_95": round(risk.cvar_95, 6),
            "cvar_99": round(risk.cvar_99, 6),
            "daily_pnl_mean": round(risk.daily_pnl_mean, 6),
            "daily_pnl_std": round(risk.daily_pnl_std, 6),
            "daily_pnl_skew": round(risk.daily_pnl_skew, 4),
            "daily_pnl_kurt": round(risk.daily_pnl_kurt, 4),
            "max_consecutive_losses": risk.max_consecutive_losses,
            "max_consecutive_loss_amount": round(risk.max_consecutive_loss_amount, 6),
        },
        "monthly_returns": _monthly_returns(equity_curve),
        "yearly_returns": _yearly_returns(equity_curve),
    }
