from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Strategy comparison
# ---------------------------------------------------------------------------

class ComparisonRequest(BaseModel):
    task_ids: list[str] = Field(..., min_length=2, description="List of completed backtest task IDs to compare")
    weights: Optional[list[float]] = Field(
        default=None,
        description="Portfolio weights per strategy (equal if omitted, must sum to 1)"
    )


class StrategyComparisonEntry(BaseModel):
    task_id: str
    strategy_name: Optional[str] = None
    symbol: Optional[str] = None
    total_return: float
    annualised_return: float
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    annualised_volatility: float
    total_trades: int
    var_95: float
    cvar_95: float


class CorrelationPair(BaseModel):
    strategy_a: str
    strategy_b: str
    correlation: float


class CorrelationAnalysisResult(BaseModel):
    strategy_names: list[str]
    correlation_matrix: list[list[float]]
    pairwise: list[CorrelationPair]


class ComparisonResponse(BaseModel):
    strategies: list[StrategyComparisonEntry]
    best_sharpe: str        # task_id of strategy with highest Sharpe
    best_return: str        # task_id of strategy with highest total return
    lowest_drawdown: str    # task_id of strategy with lowest max drawdown
    correlation: CorrelationAnalysisResult


# ---------------------------------------------------------------------------
# Stress test
# ---------------------------------------------------------------------------

class StressScenarioResult(BaseModel):
    scenario_name: str
    peak_drawdown: float
    final_equity_ratio: float
    recovery_periods: Optional[int] = None
    metrics: dict


class StressTestResponse(BaseModel):
    task_id: str
    strategy_name: Optional[str] = None
    scenarios: list[StressScenarioResult]


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

class MonteCarloRequest(BaseModel):
    n_simulations: int = Field(default=1000, ge=100, le=10000)
    n_periods: Optional[int] = Field(default=None, ge=1, le=3650)


class MonteCarloResponse(BaseModel):
    task_id: str
    strategy_name: Optional[str] = None
    n_simulations: int
    n_periods: int
    percentiles: dict[str, list[float]]          # p5 / p25 / p50 / p75 / p95 equity curves
    final_equity_distribution: dict[str, float]  # p5 … p95 of terminal equity
    prob_positive: float
    prob_max_dd_exceeded: dict[str, float]


# ---------------------------------------------------------------------------
# Portfolio risk
# ---------------------------------------------------------------------------

class MarginalRiskContribution(BaseModel):
    strategy: str
    weight: float
    marginal_var_contribution: float
    individual_volatility: float


class PortfolioRiskResponse(BaseModel):
    n_strategies: int
    task_ids: list[str]
    weights: list[float]
    diversification_ratio: float
    metrics: dict
    marginal_risk_contributions: list[MarginalRiskContribution]
