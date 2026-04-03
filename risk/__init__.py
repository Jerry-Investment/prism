"""PRISM Risk Module — Public API.

Provides risk metric calculations, circuit breaker, limit enforcement,
and portfolio aggregation for the PRISM backtesting platform.

Quick-start
-----------
    from risk import (
        calculate_metrics,
        CircuitBreaker, CircuitBreakerConfig,
        LimitChecker, RiskSnapshot, DEFAULT_LIMITS,
        PortfolioAggregator,
    )

    # 1. Compute metrics from a backtest returns series
    metrics = calculate_metrics(returns=[0.01, -0.02, 0.03, ...])

    # 2. Set up circuit breaker
    cb = CircuitBreaker(CircuitBreakerConfig(max_daily_drawdown=0.05))

    # 3. Check risk limits
    checker = LimitChecker(DEFAULT_LIMITS)
    report = checker.check(RiskSnapshot(daily_pnl=-0.06))
    if report.breached:
        cb.trip_manual("Limit breach detected")

    # 4. Aggregate portfolio risk
    agg = PortfolioAggregator(initial_capital=10_000_000)
    agg.open_position("KRW-BTC", quantity=0.05, entry_price=85_000_000)
    agg.mark_to_market({"KRW-BTC": 84_000_000})
    snapshot = agg.snapshot(var_95=metrics.risk.var_95)
    cb.evaluate(**snapshot.__dict__)
"""

from .aggregator import PortfolioAggregator, Position, TradeFill
from .circuit_breaker import (
    CBState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerEvent,
    TripReason,
)
from .limits import (
    DEFAULT_LIMITS,
    LimitCheckReport,
    LimitChecker,
    LimitType,
    LimitViolation,
    RiskLimit,
    RiskSnapshot,
    Severity,
)
from .metrics import (
    CombinedMetrics,
    MetricsCalculator,
    PerformanceMetrics,
    RiskMetrics,
    calculate_metrics,
)

__all__ = [
    # metrics
    "calculate_metrics",
    "MetricsCalculator",
    "CombinedMetrics",
    "PerformanceMetrics",
    "RiskMetrics",
    # circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerEvent",
    "CBState",
    "TripReason",
    # limits
    "RiskLimit",
    "LimitType",
    "LimitChecker",
    "RiskSnapshot",
    "LimitCheckReport",
    "LimitViolation",
    "Severity",
    "DEFAULT_LIMITS",
    # aggregator
    "PortfolioAggregator",
    "Position",
    "TradeFill",
]
