"""
Strategy base class — ARIA will implement concrete strategies on top of this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class Signal:
    timestamp: str
    symbol: str
    action: str  # "buy" | "sell" | "hold"
    size: float = 1.0  # fraction of portfolio (0.0–1.0)
    price: Optional[float] = None
    metadata: dict = field(default_factory=dict)


class Strategy(ABC):
    """Abstract base class for all PRISM trading strategies."""

    name: str = "BaseStrategy"
    description: str = ""
    parameters: dict = {}

    def __init__(self, params: Optional[dict] = None):
        if params:
            self.parameters = {**self.parameters, **params}

    @abstractmethod
    def generate_signals(self, ohlcv: pd.DataFrame) -> list[Signal]:
        """
        Given a DataFrame with columns [timestamp, open, high, low, close, volume],
        return a list of Signal objects.
        """
        ...

    def validate_params(self) -> None:
        """Override to add parameter validation."""
        pass
