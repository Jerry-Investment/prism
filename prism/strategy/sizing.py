"""
PRISM Position Sizing Module

Defines the PositionSize data container and PositionSizer interface,
plus two built-in sizers:

  - FixedFractionSizer  : allocate a fixed % of portfolio per trade
  - VolatilityTargetSizer: ATR-based volatility-targeted sizing
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from .base import Signal


@dataclass
class PositionSize:
    """
    Result of position sizing for a single signal.

    Attributes:
        asset:           Ticker symbol.
        quantity:        Number of units (shares / coins) to trade.
        notional_value:  Trade value in base currency (KRW).
        position_pct:    Fraction of portfolio value (0.0 – 1.0).
        note:            Human-readable rationale (optional).
    """

    asset: str
    quantity: float
    notional_value: float
    position_pct: float
    note: str = ""

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError(f"quantity must be >= 0, got {self.quantity}")
        if self.notional_value < 0:
            raise ValueError(f"notional_value must be >= 0, got {self.notional_value}")
        if not 0.0 <= self.position_pct <= 1.0:
            raise ValueError(
                f"position_pct must be in [0, 1], got {self.position_pct}"
            )


class PositionSizer(abc.ABC):
    """Abstract base for position sizing strategies."""

    @abc.abstractmethod
    def size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> PositionSize:
        """
        Compute the position size for a given signal.

        Args:
            signal:            The trading signal to size.
            portfolio_value:   Total portfolio value in KRW.
            current_positions: Optional map of ticker -> current held quantity.

        Returns:
            PositionSize with quantity, notional, and position_pct filled.
        """


class FixedFractionSizer(PositionSizer):
    """
    Allocate a fixed fraction of the portfolio to each trade.

    This is the simplest, most predictable sizer and the recommended
    default for new strategies.

    Args:
        fraction: Portfolio fraction per trade (default 0.1 = 10%).
    """

    def __init__(self, fraction: float = 0.10) -> None:
        if not 0.0 < fraction <= 1.0:
            raise ValueError(f"fraction must be in (0, 1], got {fraction}")
        self.fraction = fraction

    def size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> PositionSize:
        notional = portfolio_value * self.fraction * signal.strength
        quantity = notional / signal.price if signal.price > 0 else 0.0
        return PositionSize(
            asset=signal.asset,
            quantity=quantity,
            notional_value=notional,
            position_pct=self.fraction * signal.strength,
            note=f"FixedFraction(fraction={self.fraction}, strength={signal.strength:.2f})",
        )


class VolatilityTargetSizer(PositionSizer):
    """
    Size positions so that each trade contributes a target daily volatility
    to the portfolio (ATR-based).

    The idea: allocate more to low-volatility assets and less to
    high-volatility assets so that each position contributes roughly
    equal risk.

    Args:
        target_vol_pct: Target daily portfolio vol per position
                        as a fraction of portfolio value (default 0.01 = 1%).
        atr_data:       Pre-computed ATR series keyed by ticker.
                        Must be provided at construction time.
    """

    def __init__(
        self,
        target_vol_pct: float = 0.01,
        atr_data: Optional[Dict[str, pd.Series]] = None,
    ) -> None:
        if not 0.0 < target_vol_pct <= 1.0:
            raise ValueError(
                f"target_vol_pct must be in (0, 1], got {target_vol_pct}"
            )
        self.target_vol_pct = target_vol_pct
        self.atr_data: Dict[str, pd.Series] = atr_data or {}

    def size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> PositionSize:
        atr_series = self.atr_data.get(signal.asset)

        if atr_series is None or atr_series.empty:
            # Fall back to 1% of portfolio when ATR unavailable
            notional = portfolio_value * 0.01 * signal.strength
            note = "VolatilityTarget: ATR unavailable, used 1% fallback"
        else:
            # Use most recent ATR value
            atr_value = float(atr_series.iloc[-1])
            if atr_value <= 0:
                notional = portfolio_value * 0.01 * signal.strength
                note = "VolatilityTarget: ATR=0, used 1% fallback"
            else:
                # Dollar value of 1 ATR move on 1 unit
                dollar_atr = atr_value  # already in price units

                # units = (portfolio * target_vol_pct) / dollar_atr
                target_dollar_risk = portfolio_value * self.target_vol_pct * signal.strength
                quantity = target_dollar_risk / dollar_atr
                notional = quantity * signal.price
                position_pct = min(notional / portfolio_value, 1.0)
                return PositionSize(
                    asset=signal.asset,
                    quantity=quantity,
                    notional_value=notional,
                    position_pct=position_pct,
                    note=(
                        f"VolatilityTarget(target_vol={self.target_vol_pct:.2%}, "
                        f"atr={atr_value:.4f}, strength={signal.strength:.2f})"
                    ),
                )

        quantity = notional / signal.price if signal.price > 0 else 0.0
        position_pct = min(notional / portfolio_value, 1.0) if portfolio_value > 0 else 0.0
        return PositionSize(
            asset=signal.asset,
            quantity=quantity,
            notional_value=notional,
            position_pct=position_pct,
            note=note,
        )
