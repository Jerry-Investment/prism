"""PRISM Risk Module — Performance & Risk Metric Calculations.

Calculates:
  Performance: Sharpe, Sortino, Max Drawdown, Win Rate, Profit Factor
  Risk:        VaR, CVaR, daily P&L distribution stats, max consecutive losses
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class PerformanceMetrics:
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float          # absolute fraction, e.g. 0.15 = 15 %
    max_drawdown_duration: int   # number of periods
    win_rate: float              # fraction of winning trades
    profit_factor: float         # gross_profit / gross_loss
    total_return: float
    annualised_return: float
    annualised_volatility: float
    calmar_ratio: float


@dataclass
class RiskMetrics:
    var_95: float                # Value-at-Risk at 95 % confidence (1-period)
    var_99: float
    cvar_95: float               # Conditional VaR (Expected Shortfall) at 95 %
    cvar_99: float
    daily_pnl_mean: float
    daily_pnl_std: float
    daily_pnl_skew: float
    daily_pnl_kurt: float
    max_consecutive_losses: int
    max_consecutive_loss_amount: float   # sum of losses in worst streak


@dataclass
class CombinedMetrics:
    performance: PerformanceMetrics
    risk: RiskMetrics


# ---------------------------------------------------------------------------
# Core calculator
# ---------------------------------------------------------------------------

class MetricsCalculator:
    """Compute all PRISM risk and performance metrics from a returns series.

    Parameters
    ----------
    returns:
        Sequence of periodic (e.g. daily) returns as decimal fractions.
    trades:
        Optional list of per-trade P&L values (used for Win Rate / Profit Factor).
    periods_per_year:
        Trading periods in a year.  365 for 24h crypto, 252 for equities.
    risk_free_rate:
        Annual risk-free rate as decimal fraction (default 0.03 = 3 %).
    """

    def __init__(
        self,
        returns: Sequence[float],
        trades: Sequence[float] | None = None,
        periods_per_year: int = 365,
        risk_free_rate: float = 0.03,
    ) -> None:
        self._returns = np.asarray(returns, dtype=float)
        self._trades = np.asarray(trades, dtype=float) if trades is not None else self._returns
        self._n = len(self._returns)
        self._ppy = periods_per_year
        self._rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_all(self) -> CombinedMetrics:
        return CombinedMetrics(
            performance=self.compute_performance(),
            risk=self.compute_risk(),
        )

    def compute_performance(self) -> PerformanceMetrics:
        r = self._returns
        ppy = self._ppy

        total_return = float(np.prod(1 + r) - 1)
        ann_return = float((1 + total_return) ** (ppy / max(self._n, 1)) - 1)
        ann_vol = float(np.std(r, ddof=1) * math.sqrt(ppy)) if self._n > 1 else 0.0

        sharpe = self._sharpe(r, ppy)
        sortino = self._sortino(r, ppy)
        mdd, mdd_dur = self._max_drawdown(r)
        win_rate, profit_factor = self._trade_stats(self._trades)
        calmar = ann_return / max(abs(mdd), 1e-10)

        return PerformanceMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=mdd,
            max_drawdown_duration=mdd_dur,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return=total_return,
            annualised_return=ann_return,
            annualised_volatility=ann_vol,
            calmar_ratio=calmar,
        )

    def compute_risk(self) -> RiskMetrics:
        r = self._returns
        var95, cvar95 = self._var_cvar(r, 0.95)
        var99, cvar99 = self._var_cvar(r, 0.99)
        streak, streak_amt = self._max_consecutive_losses(r)

        pnl = pd.Series(r)
        return RiskMetrics(
            var_95=var95,
            var_99=var99,
            cvar_95=cvar95,
            cvar_99=cvar99,
            daily_pnl_mean=float(pnl.mean()),
            daily_pnl_std=float(pnl.std(ddof=1)) if len(pnl) > 1 else 0.0,
            daily_pnl_skew=float(pnl.skew()) if len(pnl) > 2 else 0.0,
            daily_pnl_kurt=float(pnl.kurt()) if len(pnl) > 3 else 0.0,
            max_consecutive_losses=streak,
            max_consecutive_loss_amount=streak_amt,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sharpe(self, r: np.ndarray, ppy: int) -> float:
        excess = r - self._rf_per_period
        std = np.std(excess, ddof=1)
        if std < 1e-10 or self._n < 2:
            return 0.0
        return float(np.mean(excess) / std * math.sqrt(ppy))

    def _sortino(self, r: np.ndarray, ppy: int) -> float:
        excess = r - self._rf_per_period
        downside = excess[excess < 0]
        if len(downside) == 0:
            return float("inf")
        downside_std = math.sqrt(np.mean(downside ** 2))
        if downside_std < 1e-10:
            return 0.0
        return float(np.mean(excess) / downside_std * math.sqrt(ppy))

    @staticmethod
    def _max_drawdown(r: np.ndarray) -> tuple[float, int]:
        """Return (max_drawdown_fraction, duration_in_periods)."""
        if len(r) == 0:
            return 0.0, 0
        cum = np.cumprod(1 + r)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / peak
        mdd = float(np.min(dd))

        # duration: longest period from peak to trough
        in_dd = dd < 0
        max_dur = 0
        cur_dur = 0
        for flag in in_dd:
            if flag:
                cur_dur += 1
                max_dur = max(max_dur, cur_dur)
            else:
                cur_dur = 0
        return mdd, max_dur

    @staticmethod
    def _trade_stats(trades: np.ndarray) -> tuple[float, float]:
        if len(trades) == 0:
            return 0.0, 0.0
        wins = trades[trades > 0]
        losses = trades[trades < 0]
        win_rate = len(wins) / len(trades)
        gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
        gross_loss = float(abs(np.sum(losses))) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / max(gross_loss, 1e-10)
        return win_rate, profit_factor

    @staticmethod
    def _var_cvar(r: np.ndarray, confidence: float) -> tuple[float, float]:
        """Historical VaR and CVaR (negative numbers = losses)."""
        if len(r) == 0:
            return 0.0, 0.0
        sorted_r = np.sort(r)
        idx = int(math.floor((1 - confidence) * len(sorted_r)))
        var = float(sorted_r[max(idx, 0)])
        cvar = float(np.mean(sorted_r[: max(idx, 1)]))
        return var, cvar

    @staticmethod
    def _max_consecutive_losses(r: np.ndarray) -> tuple[int, float]:
        """Return (max_streak_count, sum_of_losses_in_worst_streak)."""
        max_streak = 0
        max_amt = 0.0
        cur_streak = 0
        cur_amt = 0.0
        for ret in r:
            if ret < 0:
                cur_streak += 1
                cur_amt += ret
                if cur_streak > max_streak:
                    max_streak = cur_streak
                    max_amt = cur_amt
            else:
                cur_streak = 0
                cur_amt = 0.0
        return max_streak, max_amt


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def calculate_metrics(
    returns: Sequence[float],
    trades: Sequence[float] | None = None,
    periods_per_year: int = 365,
    risk_free_rate: float = 0.03,
) -> CombinedMetrics:
    """Convenience wrapper: compute all metrics from a returns sequence."""
    return MetricsCalculator(returns, trades, periods_per_year, risk_free_rate).compute_all()
