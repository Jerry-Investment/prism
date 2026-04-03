"""
Example: Moving Average Crossover Strategy

Demonstrates how to implement a concrete strategy using the PRISM
strategy framework.  This strategy goes long when the fast MA crosses
above the slow MA and exits (sells) when it crosses back below.

Usage::

    strategy = MACrossStrategy(params={"fast_window": 10, "slow_window": 30})
    signals = strategy.generate_signals({"BTC/KRW": ohlcv_df})
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from prism.strategy.base import AssetType, Signal, SignalDirection, Strategy
from prism.strategy.indicators import Indicators
from prism.strategy.params import ParamSpec, ParamType
from prism.strategy.sizing import FixedFractionSizer, PositionSize


class MACrossStrategy(Strategy):
    """
    Simple Moving Average Crossover strategy.

    Signals:
        BUY  — fast MA crosses above slow MA
        SELL — fast MA crosses below slow MA
    """

    param_specs = [
        ParamSpec(
            "fast_window",
            ParamType.INT,
            default=10,
            required=True,
            min_val=2,
            max_val=100,
            description="Fast SMA window (bars)",
        ),
        ParamSpec(
            "slow_window",
            ParamType.INT,
            default=30,
            required=True,
            min_val=5,
            max_val=500,
            description="Slow SMA window (bars)",
        ),
        ParamSpec(
            "asset_type",
            ParamType.STR,
            default="crypto",
            choices=["crypto", "stock_kr", "stock_foreign"],
            description="Asset class of target instrument",
        ),
        ParamSpec(
            "position_fraction",
            ParamType.FLOAT,
            default=0.10,
            min_val=0.01,
            max_val=1.0,
            description="Portfolio fraction per trade",
        ),
    ]

    def _validate_params(self) -> None:
        super()._validate_params()
        if self.params["fast_window"] >= self.params["slow_window"]:
            raise ValueError(
                f"fast_window ({self.params['fast_window']}) must be "
                f"< slow_window ({self.params['slow_window']})"
            )

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        signals: List[Signal] = []
        asset_type = AssetType(self.params["asset_type"])

        for ticker, df in data.items():
            if len(df) < self.params["slow_window"]:
                continue  # not enough history

            fast_ma = Indicators.sma(df["close"], self.params["fast_window"])
            slow_ma = Indicators.sma(df["close"], self.params["slow_window"])

            cross_above = Indicators.crossover(fast_ma, slow_ma)
            cross_below = Indicators.crossunder(fast_ma, slow_ma)

            # Only look at the last bar for signal generation
            ts = df.index[-1]
            close_price = float(df["close"].iloc[-1])

            if cross_above.iloc[-1]:
                signals.append(
                    Signal(
                        timestamp=ts,
                        asset=ticker,
                        asset_type=asset_type,
                        direction=SignalDirection.BUY,
                        strength=1.0,
                        price=close_price,
                        meta={
                            "fast_ma": float(fast_ma.iloc[-1]),
                            "slow_ma": float(slow_ma.iloc[-1]),
                        },
                    )
                )
            elif cross_below.iloc[-1]:
                signals.append(
                    Signal(
                        timestamp=ts,
                        asset=ticker,
                        asset_type=asset_type,
                        direction=SignalDirection.SELL,
                        strength=1.0,
                        price=close_price,
                        meta={
                            "fast_ma": float(fast_ma.iloc[-1]),
                            "slow_ma": float(slow_ma.iloc[-1]),
                        },
                    )
                )

        return signals

    def calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: Dict[str, float],
    ) -> PositionSize:
        sizer = FixedFractionSizer(fraction=self.params["position_fraction"])
        return sizer.size(signal, portfolio_value, current_positions)
