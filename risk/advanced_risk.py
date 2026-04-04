"""PRISM Advanced Risk Module — Stress Testing, Monte Carlo, Portfolio & Correlation Analysis.

Provides:
  StressTester    — apply named historical crisis scenarios to a returns series
  MonteCarloEngine — bootstrap / parametric Monte Carlo simulation
  CorrelationAnalyzer — pairwise return correlation between strategies
  PortfolioRiskCalculator — combined risk for a multi-strategy portfolio
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

from risk.metrics import MetricsCalculator, CombinedMetrics


# ---------------------------------------------------------------------------
# Stress-test scenarios
# ---------------------------------------------------------------------------

# Each scenario is a list of daily shocked returns applied at the start of
# the simulation.  They are drawn from documented crypto/equity crisis periods.
STRESS_SCENARIOS: dict[str, list[float]] = {
    "covid_crash_2020": [
        # Feb 20 – Mar 13 2020: BTC fell ~50 % in ~3 weeks (21 trading days)
        -0.030, -0.028, -0.015, -0.040, -0.055, -0.070, -0.080,
        -0.120, -0.145, -0.050, -0.030, -0.020, +0.025, +0.030,
        +0.015, -0.010, -0.005, +0.010, +0.020, +0.035, +0.040,
    ],
    "crypto_bear_2022": [
        # 2022 bear: BTC lost ~65 % over the year — month-by-month daily avg
        -0.005, -0.004, -0.006, -0.008, -0.010, -0.012, -0.015,
        -0.020, -0.025, -0.018, -0.010, -0.008, -0.005, -0.003,
        +0.002, -0.004, -0.006, -0.008, -0.012, -0.015, -0.010,
        -0.008, -0.006, -0.005, -0.004, -0.003, +0.001, +0.002,
        +0.003, +0.002,
    ],
    "luna_ust_collapse_2022": [
        # May 7–12 2022: Terra/LUNA ecosystem collapse, BTC -35 % in 5 days
        -0.050, -0.080, -0.120, -0.150, -0.100, -0.060,
        -0.030, -0.020, -0.010, +0.015, +0.025, +0.020,
    ],
    "ftx_collapse_2022": [
        # Nov 6–12 2022: FTX collapse, BTC -25 % in 5 days
        -0.030, -0.060, -0.090, -0.080, -0.040, -0.020,
        -0.010, +0.010, +0.020, +0.015,
    ],
    "gfc_2008_equity": [
        # Sep–Oct 2008 GFC: KOSPI lost ~40 % in 2 months
        -0.025, -0.030, -0.040, -0.050, -0.045, -0.035,
        -0.030, -0.025, -0.020, -0.015, +0.010, +0.015,
        +0.020, +0.010, -0.005, -0.010, -0.015, -0.020,
        -0.025, -0.030, +0.015, +0.020, +0.025,
    ],
}


@dataclass
class StressTestResult:
    scenario_name: str
    shocked_returns: list[float]         # returns after applying shock
    original_returns: list[float]        # baseline returns (pre-shock horizon)
    peak_drawdown: float                 # worst drawdown during shock
    final_equity_ratio: float            # final_equity / initial (1.0 = breakeven)
    recovery_periods: int | None         # periods to recover from trough (None = not recovered)
    metrics: dict                        # CombinedMetrics as dict for the shock window


def _metrics_to_dict(m: CombinedMetrics) -> dict:
    perf = m.performance
    risk = m.risk
    sortino = perf.sortino_ratio
    return {
        "performance": {
            "sharpe_ratio": round(perf.sharpe_ratio, 4),
            "sortino_ratio": None if sortino == float("inf") else round(sortino, 4),
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
    }


class StressTester:
    """Apply named crisis scenarios to a strategy's return series.

    For each scenario, the strategy's normal returns are mixed with the
    shocked market returns to model how an unhedged position would behave
    if those conditions recurred.
    """

    def __init__(
        self,
        returns: Sequence[float],
        periods_per_year: int = 365,
        risk_free_rate: float = 0.03,
    ) -> None:
        self._returns = list(returns)
        self._ppy = periods_per_year
        self._rf = risk_free_rate

    def run_all(self) -> list[StressTestResult]:
        return [self.run(name) for name in STRESS_SCENARIOS]

    def run(self, scenario_name: str) -> StressTestResult:
        if scenario_name not in STRESS_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        shock = STRESS_SCENARIOS[scenario_name]

        # Prepend strategy returns before the shock then shock then recovery tail
        # For a fair comparison, mix: strategy_return + shock_return (additive)
        shock_len = len(shock)
        tail = self._returns[shock_len:] if len(self._returns) > shock_len else []

        mixed: list[float] = []
        for i, s in enumerate(shock):
            strat_ret = self._returns[i] if i < len(self._returns) else 0.0
            # Blend: strategy takes the shock but can partially offset via its own signal
            # We weight 80 % shock / 20 % strategy signal to model directional exposure
            mixed.append(0.8 * s + 0.2 * strat_ret)

        combined_returns = mixed + list(tail)

        # Drawdown during shock window
        shock_arr = np.array(mixed)
        cum = np.cumprod(1 + shock_arr)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / np.where(peak > 0, peak, 1)
        peak_dd = float(np.min(dd)) if len(dd) > 0 else 0.0

        final_eq_ratio = float(cum[-1]) if len(cum) > 0 else 1.0

        # Recovery: periods for cum_equity to return to pre-shock level (1.0)
        recovery = None
        if len(combined_returns) > shock_len:
            # look beyond the shock window
            post_shock = np.array(combined_returns[shock_len:])
            cum_post = float(cum[-1]) * np.cumprod(1 + post_shock)
            recovered_idx = np.where(cum_post >= 1.0)[0]
            if len(recovered_idx) > 0:
                recovery = int(recovered_idx[0]) + shock_len

        calc = MetricsCalculator(combined_returns, None, self._ppy, self._rf)
        metrics = _metrics_to_dict(calc.compute_all())

        return StressTestResult(
            scenario_name=scenario_name,
            shocked_returns=mixed,
            original_returns=list(self._returns[:shock_len]),
            peak_drawdown=peak_dd,
            final_equity_ratio=final_eq_ratio,
            recovery_periods=recovery,
            metrics=metrics,
        )


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloResult:
    n_simulations: int
    n_periods: int
    percentiles: dict[str, list[float]]  # {"p5": [...equity...], "p25": [...], ...}
    final_equity_distribution: dict[str, float]  # p5, p25, p50, p75, p95 of final equity
    prob_positive: float                 # fraction of sims with final equity > initial
    prob_max_dd_exceeded: dict[str, float]  # probability that max DD exceeds thresholds


class MonteCarloEngine:
    """Bootstrap Monte Carlo simulation from historical returns.

    Uses block bootstrap (block_size=5) to preserve short-term autocorrelation.
    """

    def __init__(
        self,
        returns: Sequence[float],
        periods_per_year: int = 365,
        seed: int = 42,
    ) -> None:
        self._returns = np.asarray(returns, dtype=float)
        self._ppy = periods_per_year
        self._rng = np.random.default_rng(seed)

    def run(
        self,
        n_simulations: int = 1000,
        n_periods: int | None = None,
        block_size: int = 5,
    ) -> MonteCarloResult:
        r = self._returns
        if len(r) == 0:
            return self._empty_result(n_simulations, n_periods or 365)

        n_periods = n_periods or len(r)
        all_equity: list[list[float]] = []

        for _ in range(n_simulations):
            sampled = self._block_bootstrap(r, n_periods, block_size)
            equity = list(np.cumprod(1 + sampled))
            all_equity.append(equity)

        # Transpose: shape (n_simulations, n_periods)
        arr = np.array(all_equity)  # (N, T)
        final_equities = arr[:, -1]
        prob_positive = float(np.mean(final_equities > 1.0))

        # Drawdown per simulation
        dd_thresholds = [0.05, 0.10, 0.15, 0.20, 0.30]
        prob_dd_exceeded = {}
        for thr in dd_thresholds:
            sim_max_dds = []
            for sim in arr:
                peak = np.maximum.accumulate(sim)
                dd = (sim - peak) / np.where(peak > 0, peak, 1)
                sim_max_dds.append(float(np.min(dd)))
            prob_dd_exceeded[f"{int(thr*100)}pct"] = float(
                np.mean(np.array(sim_max_dds) < -thr)
            )

        pct_labels = ["p5", "p25", "p50", "p75", "p95"]
        pct_values = [5, 25, 50, 75, 95]
        percentiles: dict[str, list[float]] = {}
        for label, pv in zip(pct_labels, pct_values):
            pct_curve = np.percentile(arr, pv, axis=0)
            percentiles[label] = [round(float(v), 6) for v in pct_curve]

        final_pct = {
            label: round(float(np.percentile(final_equities, pv)), 6)
            for label, pv in zip(pct_labels, pct_values)
        }

        return MonteCarloResult(
            n_simulations=n_simulations,
            n_periods=n_periods,
            percentiles=percentiles,
            final_equity_distribution=final_pct,
            prob_positive=round(prob_positive, 4),
            prob_max_dd_exceeded={k: round(v, 4) for k, v in prob_dd_exceeded.items()},
        )

    def _block_bootstrap(
        self, returns: np.ndarray, n_periods: int, block_size: int
    ) -> np.ndarray:
        n = len(returns)
        blocks_needed = math.ceil(n_periods / block_size)
        sampled = []
        for _ in range(blocks_needed):
            start = int(self._rng.integers(0, max(n - block_size, 1)))
            block = returns[start : start + block_size]
            sampled.extend(block)
        return np.array(sampled[:n_periods])

    @staticmethod
    def _empty_result(n_simulations: int, n_periods: int) -> MonteCarloResult:
        return MonteCarloResult(
            n_simulations=n_simulations,
            n_periods=n_periods,
            percentiles={k: [1.0] * n_periods for k in ["p5", "p25", "p50", "p75", "p95"]},
            final_equity_distribution={k: 1.0 for k in ["p5", "p25", "p50", "p75", "p95"]},
            prob_positive=0.0,
            prob_max_dd_exceeded={},
        )


# ---------------------------------------------------------------------------
# Correlation analysis
# ---------------------------------------------------------------------------

@dataclass
class CorrelationResult:
    strategy_names: list[str]
    correlation_matrix: list[list[float]]   # NxN
    pairwise: list[dict]                    # [{name_a, name_b, correlation}]


class CorrelationAnalyzer:
    """Compute pairwise return correlations between strategies."""

    @staticmethod
    def compute(
        strategies: dict[str, Sequence[float]],
    ) -> CorrelationResult:
        names = list(strategies.keys())
        n = len(names)

        # Align on shortest series
        min_len = min(len(v) for v in strategies.values())
        df = pd.DataFrame(
            {name: list(strategies[name])[:min_len] for name in names}
        )
        corr = df.corr(method="pearson")

        matrix = [[round(float(corr.loc[a, b]), 4) for b in names] for a in names]
        pairwise = [
            {"strategy_a": names[i], "strategy_b": names[j], "correlation": matrix[i][j]}
            for i in range(n)
            for j in range(i + 1, n)
        ]

        return CorrelationResult(
            strategy_names=names,
            correlation_matrix=matrix,
            pairwise=pairwise,
        )


# ---------------------------------------------------------------------------
# Portfolio-level risk
# ---------------------------------------------------------------------------

@dataclass
class PortfolioRiskResult:
    n_strategies: int
    weights: list[float]
    portfolio_returns: list[float]
    metrics: dict                     # CombinedMetrics as dict
    diversification_ratio: float      # weighted avg individual vol / portfolio vol
    marginal_risk_contributions: list[dict]  # [{strategy, weight, marginal_var}]


class PortfolioRiskCalculator:
    """Compute combined risk for a multi-strategy portfolio.

    Parameters
    ----------
    strategies:
        {name: returns_sequence} mapping.
    weights:
        Optional weight per strategy (must sum to 1).  Equal weights if None.
    periods_per_year:
        Trading periods in a year.
    """

    def __init__(
        self,
        strategies: dict[str, Sequence[float]],
        weights: list[float] | None = None,
        periods_per_year: int = 365,
        risk_free_rate: float = 0.03,
    ) -> None:
        self._names = list(strategies.keys())
        n = len(self._names)
        if weights is None:
            self._weights = [1.0 / n] * n
        else:
            if len(weights) != n:
                raise ValueError("weights length must match number of strategies")
            total = sum(weights)
            self._weights = [w / total for w in weights]

        min_len = min(len(v) for v in strategies.values())
        self._returns_matrix = np.array(
            [list(strategies[name])[:min_len] for name in self._names]
        )  # shape (n_strategies, n_periods)
        self._ppy = periods_per_year
        self._rf = risk_free_rate

    def compute(self) -> PortfolioRiskResult:
        w = np.array(self._weights)
        # Portfolio returns: weighted sum of strategy returns
        portfolio_returns = np.dot(w, self._returns_matrix)

        calc = MetricsCalculator(portfolio_returns, None, self._ppy, self._rf)
        metrics = _metrics_to_dict(calc.compute_all())

        # Diversification ratio = weighted avg individual vol / portfolio vol
        individual_vols = np.std(self._returns_matrix, axis=1, ddof=1)
        weighted_avg_vol = float(np.dot(w, individual_vols))
        portfolio_vol = float(np.std(portfolio_returns, ddof=1)) if len(portfolio_returns) > 1 else 1e-10
        div_ratio = weighted_avg_vol / max(portfolio_vol, 1e-10)

        # Marginal VaR contributions
        marginal_contributions = []
        port_var_95 = float(np.percentile(portfolio_returns, 5))
        for i, name in enumerate(self._names):
            strat_returns = self._returns_matrix[i]
            # Component VaR: weight * covariance(strategy, portfolio) / portfolio_std
            cov = float(np.cov(strat_returns, portfolio_returns)[0, 1]) if len(strat_returns) > 1 else 0.0
            marginal_var = w[i] * cov / max(portfolio_vol ** 2, 1e-10) * abs(port_var_95)
            marginal_contributions.append({
                "strategy": name,
                "weight": round(float(w[i]), 4),
                "marginal_var_contribution": round(marginal_var, 6),
                "individual_volatility": round(float(individual_vols[i]), 6),
            })

        return PortfolioRiskResult(
            n_strategies=len(self._names),
            weights=list(w),
            portfolio_returns=list(portfolio_returns),
            metrics=metrics,
            diversification_ratio=round(div_ratio, 4),
            marginal_risk_contributions=marginal_contributions,
        )
