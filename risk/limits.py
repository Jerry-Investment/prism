"""PRISM Risk Module — Risk Limit Definitions and Violation Detection.

Defines a set of named risk limits and provides a checker that evaluates
a snapshot of current portfolio/position state against those limits.

Design goals
------------
* Limits are declarative data objects — easy to configure or load from JSON/DB.
* The LimitChecker is stateless per evaluation; call it on every heartbeat.
* Violations include severity levels so downstream consumers can triage.

Usage example
-------------
    limits = [
        RiskLimit("daily_drawdown",    LimitType.MAX_DAILY_DRAWDOWN,   0.05),
        RiskLimit("position_size_btc", LimitType.MAX_POSITION_SIZE,    0.20),
        RiskLimit("portfolio_dd",      LimitType.MAX_PORTFOLIO_DD,     0.15),
        RiskLimit("leverage",          LimitType.MAX_LEVERAGE,         3.0),
    ]
    checker = LimitChecker(limits)

    snapshot = RiskSnapshot(
        daily_pnl=-0.06,
        portfolio_drawdown=0.08,
        position_sizes={"KRW-BTC": 0.22},
        leverage=1.5,
    )
    report = checker.check(snapshot)
    for v in report.violations:
        alert(v.limit.name, v.severity)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Limit types
# ---------------------------------------------------------------------------

class LimitType(Enum):
    MAX_DAILY_DRAWDOWN = "max_daily_drawdown"          # fraction of daily capital
    MAX_PORTFOLIO_DD = "max_portfolio_drawdown"         # fraction from equity peak
    MAX_POSITION_SIZE = "max_position_size"             # fraction of total capital
    MAX_LEVERAGE = "max_leverage"                       # gross exposure / equity
    MAX_CONSECUTIVE_LOSSES = "max_consecutive_losses"   # integer count
    MAX_VAR_95 = "max_var_95"                           # 1-period 95% VaR (fraction)
    MIN_WIN_RATE = "min_win_rate"                       # fraction, warns if below
    MIN_PROFIT_FACTOR = "min_profit_factor"             # warns if below threshold


class Severity(Enum):
    WARNING = "warning"    # approaching limit
    BREACH = "breach"      # limit exceeded


# ---------------------------------------------------------------------------
# Risk limit definition
# ---------------------------------------------------------------------------

@dataclass
class RiskLimit:
    """A single named risk limit with an optional warning level.

    Parameters
    ----------
    name:        Human-readable identifier.
    limit_type:  Which metric this limit applies to.
    hard_limit:  Value at which a BREACH is declared.
    warn_pct:    Fraction of hard_limit at which a WARNING fires (default 0.8).
                 e.g. hard_limit=0.05, warn_pct=0.8 → warn at 0.04.
    active:      Whether this limit is currently enforced.
    """

    name: str
    limit_type: LimitType
    hard_limit: float
    warn_pct: float = 0.80
    active: bool = True

    @property
    def warn_limit(self) -> float:
        return self.hard_limit * self.warn_pct


# ---------------------------------------------------------------------------
# Snapshot of current portfolio state
# ---------------------------------------------------------------------------

@dataclass
class RiskSnapshot:
    """Point-in-time risk state submitted to the LimitChecker.

    All fractions are decimal (0.05 = 5 %).  Missing / unknown fields
    default to 0 / empty so callers only need to populate what they have.
    """

    daily_pnl: float = 0.0                        # negative = loss today
    portfolio_drawdown: float = 0.0               # positive fraction from peak
    position_sizes: dict[str, float] = field(default_factory=dict)  # symbol → fraction
    leverage: float = 1.0
    consecutive_losses: int = 0
    var_95: float = 0.0                           # current period VaR (negative)
    win_rate: float = 1.0
    profit_factor: float = 999.0

    def largest_position(self) -> float:
        return max(self.position_sizes.values(), default=0.0)


# ---------------------------------------------------------------------------
# Violation result
# ---------------------------------------------------------------------------

@dataclass
class LimitViolation:
    limit: RiskLimit
    severity: Severity
    observed: Any
    threshold: Any
    message: str = ""

    def __str__(self) -> str:
        return (
            f"[{self.severity.value.upper()}] {self.limit.name}: "
            f"observed={self.observed:.4g} vs {self.severity.value}={self.threshold:.4g}"
            + (f" — {self.message}" if self.message else "")
        )


@dataclass
class LimitCheckReport:
    violations: list[LimitViolation] = field(default_factory=list)
    snapshot: RiskSnapshot | None = None

    @property
    def breached(self) -> bool:
        return any(v.severity == Severity.BREACH for v in self.violations)

    @property
    def warned(self) -> bool:
        return any(v.severity == Severity.WARNING for v in self.violations)

    @property
    def clean(self) -> bool:
        return len(self.violations) == 0

    def breaches(self) -> list[LimitViolation]:
        return [v for v in self.violations if v.severity == Severity.BREACH]

    def warnings(self) -> list[LimitViolation]:
        return [v for v in self.violations if v.severity == Severity.WARNING]

    def summary(self) -> str:
        if self.clean:
            return "All risk limits within bounds."
        lines = [str(v) for v in self.violations]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Limit checker
# ---------------------------------------------------------------------------

class LimitChecker:
    """Evaluates a RiskSnapshot against a list of RiskLimits."""

    def __init__(self, limits: list[RiskLimit]) -> None:
        self._limits = [lim for lim in limits if lim.active]

    def check(self, snapshot: RiskSnapshot) -> LimitCheckReport:
        report = LimitCheckReport(snapshot=snapshot)

        for lim in self._limits:
            observed = self._extract(lim.limit_type, snapshot)
            violation = self._evaluate(lim, observed)
            if violation:
                report.violations.append(violation)

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract(limit_type: LimitType, snap: RiskSnapshot) -> float:
        mapping: dict[LimitType, float] = {
            LimitType.MAX_DAILY_DRAWDOWN:       abs(min(snap.daily_pnl, 0)),
            LimitType.MAX_PORTFOLIO_DD:         snap.portfolio_drawdown,
            LimitType.MAX_POSITION_SIZE:        snap.largest_position(),
            LimitType.MAX_LEVERAGE:             snap.leverage,
            LimitType.MAX_CONSECUTIVE_LOSSES:   float(snap.consecutive_losses),
            LimitType.MAX_VAR_95:               abs(min(snap.var_95, 0)),
            LimitType.MIN_WIN_RATE:             snap.win_rate,
            LimitType.MIN_PROFIT_FACTOR:        snap.profit_factor,
        }
        return mapping.get(limit_type, 0.0)

    @staticmethod
    def _evaluate(lim: RiskLimit, observed: float) -> LimitViolation | None:
        is_min_type = lim.limit_type in (
            LimitType.MIN_WIN_RATE,
            LimitType.MIN_PROFIT_FACTOR,
        )

        if is_min_type:
            # For minimums: breach if below hard_limit, warn if below warn_limit
            if observed < lim.hard_limit:
                return LimitViolation(
                    limit=lim,
                    severity=Severity.BREACH,
                    observed=observed,
                    threshold=lim.hard_limit,
                )
            if observed < lim.warn_limit:
                return LimitViolation(
                    limit=lim,
                    severity=Severity.WARNING,
                    observed=observed,
                    threshold=lim.warn_limit,
                )
        else:
            # For maximums: breach if above hard_limit, warn if above warn_limit
            if observed > lim.hard_limit:
                return LimitViolation(
                    limit=lim,
                    severity=Severity.BREACH,
                    observed=observed,
                    threshold=lim.hard_limit,
                )
            if observed > lim.warn_limit:
                return LimitViolation(
                    limit=lim,
                    severity=Severity.WARNING,
                    observed=observed,
                    threshold=lim.warn_limit,
                )
        return None


# ---------------------------------------------------------------------------
# Default PRISM risk limits (can be overridden via JERRY's config)
# ---------------------------------------------------------------------------

DEFAULT_LIMITS: list[RiskLimit] = [
    RiskLimit("daily_drawdown",       LimitType.MAX_DAILY_DRAWDOWN,     0.05),
    RiskLimit("portfolio_drawdown",   LimitType.MAX_PORTFOLIO_DD,       0.15),
    RiskLimit("max_position_size",    LimitType.MAX_POSITION_SIZE,      0.30),
    RiskLimit("max_leverage",         LimitType.MAX_LEVERAGE,           3.0),
    RiskLimit("consecutive_losses",   LimitType.MAX_CONSECUTIVE_LOSSES, 5.0),
    RiskLimit("var_95_limit",         LimitType.MAX_VAR_95,             0.03),
    RiskLimit("min_win_rate",         LimitType.MIN_WIN_RATE,           0.40, warn_pct=1.25),
    RiskLimit("min_profit_factor",    LimitType.MIN_PROFIT_FACTOR,      1.0,  warn_pct=1.25),
]
