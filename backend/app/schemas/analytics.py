from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    sharpe_ratio: float
    sortino_ratio: Optional[float]
    max_drawdown: float
    max_drawdown_duration: int
    win_rate: float
    profit_factor: float
    total_return: float
    annualised_return: float
    annualised_volatility: float
    calmar_ratio: float


class RiskMetrics(BaseModel):
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    daily_pnl_mean: float
    daily_pnl_std: float
    daily_pnl_skew: float
    daily_pnl_kurt: float
    max_consecutive_losses: int
    max_consecutive_loss_amount: float


class AnalyticsResponse(BaseModel):
    task_id: str
    strategy_name: Optional[str] = None
    symbol: Optional[str] = None
    total_trades: int = 0
    initial_capital: float = 0.0
    final_equity: float = 0.0
    performance: PerformanceMetrics
    risk: RiskMetrics
    monthly_returns: dict[str, float] = Field(default_factory=dict)
    yearly_returns: dict[str, float] = Field(default_factory=dict)
    equity_curve: list[dict] = Field(default_factory=list)
