"""PRISM Risk Module — Position & Portfolio Risk Aggregation.

Aggregates individual position risk exposures into a portfolio-level
RiskSnapshot that can be fed directly to the LimitChecker or CircuitBreaker.

Key responsibilities
--------------------
* Track open positions and their mark-to-market values
* Compute total portfolio exposure, leverage, and per-position weights
* Derive daily P&L and running drawdown from equity curve
* Produce a RiskSnapshot ready for limit evaluation

Usage example
-------------
    agg = PortfolioAggregator(initial_capital=10_000_000)

    # Open a position
    agg.open_position("KRW-BTC", quantity=0.05, entry_price=85_000_000)

    # Mark-to-market update (on every price tick or candle close)
    agg.mark_to_market({"KRW-BTC": 82_000_000})

    snapshot = agg.snapshot()
    print(snapshot.portfolio_drawdown)  # 0.015 (1.5 %)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

from .limits import RiskSnapshot


# ---------------------------------------------------------------------------
# Position data
# ---------------------------------------------------------------------------

@dataclass
class Position:
    symbol: str
    quantity: float        # positive = long, negative = short
    entry_price: float     # average cost basis
    current_price: float = 0.0

    @property
    def notional(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return abs(self.quantity) * self.entry_price

    @property
    def unrealised_pnl(self) -> float:
        return self.quantity * (self.current_price - self.entry_price)

    @property
    def unrealised_pnl_pct(self) -> float:
        if self.cost_basis < 1e-10:
            return 0.0
        return self.unrealised_pnl / self.cost_basis


class TradeFill(NamedTuple):
    symbol: str
    quantity: float     # positive = buy, negative = sell
    price: float
    realised_pnl: float = 0.0


# ---------------------------------------------------------------------------
# Portfolio aggregator
# ---------------------------------------------------------------------------

class PortfolioAggregator:
    """Maintains running portfolio state and aggregates risk metrics.

    Parameters
    ----------
    initial_capital:
        Starting cash capital (in base currency, e.g. KRW).
    """

    def __init__(self, initial_capital: float) -> None:
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._positions: dict[str, Position] = {}

        # Equity tracking for drawdown & daily P&L
        self._equity_peak = initial_capital
        self._daily_start_equity = initial_capital
        self._realised_pnl_total = 0.0

        # Trade history for win rate / consecutive loss tracking
        self._trade_results: list[float] = []

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def open_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
    ) -> None:
        """Record a new position or add to an existing one."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            old_cost = pos.quantity * pos.entry_price
            new_cost = quantity * entry_price
            total_qty = pos.quantity + quantity
            if abs(total_qty) < 1e-12:
                del self._positions[symbol]
                return
            avg_price = (old_cost + new_cost) / total_qty
            pos.quantity = total_qty
            pos.entry_price = avg_price
            pos.current_price = entry_price
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
            )
        # Deduct cost from cash (simplified, no margin accounting)
        self._cash -= quantity * entry_price

    def close_position(self, symbol: str, exit_price: float) -> float:
        """Close an entire position, record realised P&L, return P&L."""
        if symbol not in self._positions:
            return 0.0
        pos = self._positions.pop(symbol)
        pnl = pos.quantity * (exit_price - pos.entry_price)
        self._cash += pos.quantity * exit_price
        self._realised_pnl_total += pnl
        self._trade_results.append(pnl)
        return pnl

    def apply_fill(self, fill: TradeFill) -> None:
        """Apply a trade fill (partial open/close) with realised P&L."""
        if fill.realised_pnl != 0.0:
            self._realised_pnl_total += fill.realised_pnl
            self._trade_results.append(fill.realised_pnl)
        self.open_position(fill.symbol, fill.quantity, fill.price)

    def mark_to_market(self, prices: dict[str, float]) -> None:
        """Update current prices for all positions."""
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

    # ------------------------------------------------------------------
    # Equity & drawdown helpers
    # ------------------------------------------------------------------

    def total_equity(self) -> float:
        unrealised = sum(p.unrealised_pnl for p in self._positions.values())
        return self._cash + unrealised

    def portfolio_drawdown(self) -> float:
        """Fraction below equity peak (positive value)."""
        equity = self.total_equity()
        if equity > self._equity_peak:
            self._equity_peak = equity
        if self._equity_peak < 1e-10:
            return 0.0
        return max(0.0, (self._equity_peak - equity) / self._equity_peak)

    def daily_pnl(self) -> float:
        """Fractional P&L since start of current day."""
        if self._daily_start_equity < 1e-10:
            return 0.0
        return (self.total_equity() - self._daily_start_equity) / self._daily_start_equity

    def reset_daily(self) -> None:
        """Call at the start of each trading day."""
        self._daily_start_equity = self.total_equity()

    # ------------------------------------------------------------------
    # Risk snapshot
    # ------------------------------------------------------------------

    def snapshot(self, var_95: float = 0.0) -> RiskSnapshot:
        """Build a RiskSnapshot from current state.

        Parameters
        ----------
        var_95:
            Pre-computed 1-period 95% VaR (negative fraction).
            Pass from MetricsCalculator if available.
        """
        equity = self.total_equity()
        gross_exposure = sum(abs(p.notional) for p in self._positions.values())
        leverage = gross_exposure / max(equity, 1e-10)

        position_sizes: dict[str, float] = {}
        for sym, pos in self._positions.items():
            position_sizes[sym] = abs(pos.notional) / max(equity, 1e-10)

        wins = [t for t in self._trade_results if t > 0]
        losses = [t for t in self._trade_results if t < 0]
        win_rate = len(wins) / max(len(self._trade_results), 1)
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / max(gross_loss, 1e-10)

        consecutive_losses = self._count_consecutive_losses()

        return RiskSnapshot(
            daily_pnl=self.daily_pnl(),
            portfolio_drawdown=self.portfolio_drawdown(),
            position_sizes=position_sizes,
            leverage=leverage,
            consecutive_losses=consecutive_losses,
            var_95=var_95,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------

    def position_summary(self) -> list[dict]:
        """Return a list of dicts describing open positions."""
        equity = self.total_equity()
        rows = []
        for sym, pos in self._positions.items():
            rows.append({
                "symbol": sym,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "notional": pos.notional,
                "weight": abs(pos.notional) / max(equity, 1e-10),
                "unrealised_pnl": pos.unrealised_pnl,
                "unrealised_pnl_pct": pos.unrealised_pnl_pct,
            })
        return rows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_consecutive_losses(self) -> int:
        count = 0
        for t in reversed(self._trade_results):
            if t < 0:
                count += 1
            else:
                break
        return count
