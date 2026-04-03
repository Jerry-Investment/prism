"""
PRISM Strategy Base Class

Defines the core abstractions for all trading strategies:
- Strategy: abstract base for user-defined strategies
- Signal: buy/sell/hold signal emitted by a strategy
- AssetType: enum for supported asset classes (crypto, stock, foreign stock)
- SignalDirection: enum for signal direction
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class AssetType(str, Enum):
    """Supported asset classes in PRISM."""

    CRYPTO = "crypto"          # Upbit cryptocurrencies (BTC/KRW, ETH/KRW, …)
    STOCK_KR = "stock_kr"      # KIS domestic equities (KOSPI / KOSDAQ)
    STOCK_FOREIGN = "stock_foreign"  # Foreign equities (US, etc.)


class SignalDirection(str, Enum):
    """Direction of a trading signal."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    """
    A single trading signal produced by a strategy.

    Attributes:
        timestamp:   Bar timestamp the signal is generated on.
        asset:       Ticker symbol (e.g. "BTC/KRW", "005930", "AAPL").
        asset_type:  Asset class the symbol belongs to.
        direction:   BUY / SELL / HOLD.
        strength:    Conviction weight in [0, 1].  1.0 = maximum conviction.
        price:       Reference price at signal generation (typically close).
        meta:        Arbitrary key/value metadata (indicator values, regime, …).
    """

    timestamp: pd.Timestamp
    asset: str
    asset_type: AssetType
    direction: SignalDirection
    strength: float
    price: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"Signal strength must be in [0, 1], got {self.strength}")
        if self.price <= 0:
            raise ValueError(f"Signal price must be positive, got {self.price}")


class Strategy(abc.ABC):
    """
    Abstract base class for all PRISM strategies.

    Subclass this and implement:
        - ``generate_signals``: produce signals from a multi-asset OHLCV dict
        - ``calculate_position_size``: translate a signal into a PositionSize

    Optional overrides:
        - ``on_start``: one-time setup (e.g. pre-compute indicator state)
        - ``on_end``:   teardown / final logging
        - ``_validate_params``: parameter validation beyond ParamSpec rules
        - ``param_specs``: declare expected parameters for auto-validation

    Example::

        class MACrossStrategy(Strategy):
            def generate_signals(self, data):
                df = data["BTC/KRW"]
                fast = Indicators.sma(df["close"], self.params["fast_window"])
                slow = Indicators.sma(df["close"], self.params["slow_window"])
                ...

            def calculate_position_size(self, signal, portfolio_value, positions):
                return FixedFractionSizer(fraction=0.1).size(signal, portfolio_value)
    """

    # Subclasses may override to declare parameter specs used for validation.
    param_specs: List[Any] = []

    def __init__(self, params: Optional[Dict[str, Any]] = None) -> None:
        self.params: Dict[str, Any] = params or {}
        self._validate_params()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
    ) -> List[Signal]:
        """
        Generate trading signals from current market data.

        Args:
            data: Mapping of ticker -> OHLCV DataFrame.
                  Each DataFrame must have columns:
                  ``open``, ``high``, ``low``, ``close``, ``volume``
                  and a DatetimIndex (UTC).

        Returns:
            List of Signal objects.  May be empty if no action is warranted.
        """

    @abc.abstractmethod
    def calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: Dict[str, float],
    ) -> "PositionSize":  # noqa: F821  (forward ref resolved at runtime)
        """
        Translate a signal into a concrete position size.

        Args:
            signal:            The signal to size.
            portfolio_value:   Total portfolio value in base currency (KRW).
            current_positions: Mapping of ticker -> current quantity held.

        Returns:
            PositionSize with notional and quantity computed.
        """

    # ------------------------------------------------------------------
    # Lifecycle hooks (optional overrides)
    # ------------------------------------------------------------------

    def on_start(self, data: Dict[str, pd.DataFrame]) -> None:
        """Called once before the first bar.  Override for warm-up logic."""

    def on_end(self) -> None:
        """Called after the last bar.  Override for cleanup / final logging."""

    # ------------------------------------------------------------------
    # Parameter validation
    # ------------------------------------------------------------------

    def _validate_params(self) -> None:
        """
        Validate self.params against self.param_specs.
        Override to add custom cross-parameter checks.
        """
        from .params import ParamSpec  # local import to avoid circular dep

        for spec in self.param_specs:
            if isinstance(spec, ParamSpec):
                spec.validate(self.params)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.name}(params={self.params})"
