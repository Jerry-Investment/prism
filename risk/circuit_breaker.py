"""PRISM Risk Module — Circuit Breaker Logic.

A circuit breaker monitors live trading and halts activity when
configurable thresholds are breached.

States
------
  CLOSED   — normal operation, trading allowed
  OPEN     — threshold breached, trading halted
  HALF_OPEN — cooldown elapsed; one probe trade allowed to test recovery

Usage example
-------------
    config = CircuitBreakerConfig(
        max_daily_drawdown=0.05,     # halt if daily loss > 5 %
        max_position_loss=0.10,      # halt if single position loses > 10 %
        consecutive_loss_limit=5,    # halt after 5 consecutive losses
        cooldown_seconds=3600,       # 1-hour cooldown before HALF_OPEN
    )
    cb = CircuitBreaker(config)

    # call on every fill / mark-to-market update
    event = cb.evaluate(daily_pnl=-0.06, position_pnl=-0.02, consecutive_losses=3)
    if event.tripped:
        halt_trading()
        notify_jerry(event)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class CBState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TripReason(Enum):
    DAILY_DRAWDOWN = "daily_drawdown_exceeded"
    POSITION_LOSS = "position_loss_exceeded"
    CONSECUTIVE_LOSSES = "consecutive_losses_exceeded"
    PORTFOLIO_DRAWDOWN = "portfolio_drawdown_exceeded"
    MANUAL = "manual_trip"


@dataclass
class CircuitBreakerConfig:
    # Drawdown limits (fractions, e.g. 0.05 = 5 %)
    max_daily_drawdown: float = 0.05
    max_portfolio_drawdown: float = 0.15
    max_position_loss: float = 0.10

    # Consecutive loss counter limit
    consecutive_loss_limit: int = 5

    # Cooldown before moving from OPEN → HALF_OPEN (seconds)
    cooldown_seconds: int = 3600

    # Optional alert callback — called with (CircuitBreakerEvent) on trip
    alert_callback: Callable[[CircuitBreakerEvent], None] | None = None


@dataclass
class CircuitBreakerEvent:
    tripped: bool
    state: CBState
    reason: TripReason | None
    threshold: float | int | None
    observed: float | int | None
    timestamp: float = field(default_factory=time.time)
    message: str = ""

    def summary(self) -> str:
        if not self.tripped:
            return f"[CB:{self.state.value}] No breach."
        return (
            f"[CB:TRIP] {self.reason.value} | "
            f"threshold={self.threshold} observed={self.observed} | "
            f"{self.message}"
        )


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Stateful circuit breaker for trading halt management."""

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self.config = config
        self._state = CBState.CLOSED
        self._tripped_at: float | None = None
        self._last_event: CircuitBreakerEvent | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CBState:
        self._maybe_transition_to_half_open()
        return self._state

    @property
    def trading_allowed(self) -> bool:
        return self.state in (CBState.CLOSED, CBState.HALF_OPEN)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        *,
        daily_pnl: float = 0.0,
        position_pnl: float = 0.0,
        portfolio_drawdown: float = 0.0,
        consecutive_losses: int = 0,
    ) -> CircuitBreakerEvent:
        """Check all thresholds and update state.

        Parameters
        ----------
        daily_pnl:
            Today's P&L as a fraction of starting capital (negative = loss).
        position_pnl:
            Largest single-position unrealised loss as fraction (negative = loss).
        portfolio_drawdown:
            Current portfolio drawdown from peak as fraction (positive value).
        consecutive_losses:
            Number of consecutive losing trades/periods.

        Returns
        -------
        CircuitBreakerEvent describing the evaluation result.
        """
        self._maybe_transition_to_half_open()

        # If already OPEN, do not re-evaluate thresholds
        if self._state == CBState.OPEN:
            return CircuitBreakerEvent(
                tripped=False,
                state=self._state,
                reason=self._last_event.reason if self._last_event else None,
                threshold=None,
                observed=None,
                message="Circuit breaker is OPEN — trading halted.",
            )

        # Check thresholds in priority order
        checks: list[tuple[bool, TripReason, float | int, float | int]] = [
            (
                daily_pnl < -abs(self.config.max_daily_drawdown),
                TripReason.DAILY_DRAWDOWN,
                -abs(self.config.max_daily_drawdown),
                daily_pnl,
            ),
            (
                portfolio_drawdown > self.config.max_portfolio_drawdown,
                TripReason.PORTFOLIO_DRAWDOWN,
                self.config.max_portfolio_drawdown,
                portfolio_drawdown,
            ),
            (
                position_pnl < -abs(self.config.max_position_loss),
                TripReason.POSITION_LOSS,
                -abs(self.config.max_position_loss),
                position_pnl,
            ),
            (
                consecutive_losses >= self.config.consecutive_loss_limit,
                TripReason.CONSECUTIVE_LOSSES,
                self.config.consecutive_loss_limit,
                consecutive_losses,
            ),
        ]

        for breached, reason, threshold, observed in checks:
            if breached:
                return self._trip(reason, threshold, observed)

        # No breach
        return CircuitBreakerEvent(
            tripped=False,
            state=self._state,
            reason=None,
            threshold=None,
            observed=None,
        )

    def trip_manual(self, message: str = "Manual trip by operator") -> CircuitBreakerEvent:
        """Manually open the circuit breaker (e.g. operator intervention)."""
        return self._trip(TripReason.MANUAL, threshold=None, observed=None, message=message)

    def reset(self) -> None:
        """Manually close the circuit breaker (use with caution)."""
        self._state = CBState.CLOSED
        self._tripped_at = None
        self._last_event = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trip(
        self,
        reason: TripReason,
        threshold: float | int | None,
        observed: float | int | None,
        message: str = "",
    ) -> CircuitBreakerEvent:
        self._state = CBState.OPEN
        self._tripped_at = time.time()
        if not message:
            message = (
                f"Halting trading. Threshold={threshold}, Observed={observed}."
            )
        event = CircuitBreakerEvent(
            tripped=True,
            state=CBState.OPEN,
            reason=reason,
            threshold=threshold,
            observed=observed,
            message=message,
        )
        self._last_event = event
        if self.config.alert_callback:
            try:
                self.config.alert_callback(event)
            except Exception:
                pass
        return event

    def _maybe_transition_to_half_open(self) -> None:
        if (
            self._state == CBState.OPEN
            and self._tripped_at is not None
            and (time.time() - self._tripped_at) >= self.config.cooldown_seconds
        ):
            self._state = CBState.HALF_OPEN
