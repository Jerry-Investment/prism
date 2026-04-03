"""
Moving Average Crossover Strategy

Goes long on a golden cross (fast MA crosses above slow MA) and
exits (sells) on a dead cross (fast MA crosses below slow MA).

Supports both SMA and EMA via the ``ma_type`` parameter.

Usage::

    strategy = MACrossStrategy(params={
        "fast_window": 10,
        "slow_window": 30,
        "ma_type": "ema",        # "sma" or "ema"
    })
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
    Moving Average Crossover strategy (SMA or EMA).

    Signals:
        BUY  — golden cross: fast MA crosses above slow MA
        SELL — dead cross:   fast MA crosses below slow MA
    """

    param_specs = [
        ParamSpec(
            "fast_window",
            ParamType.INT,
            default=10,
            required=True,
            min_val=2,
            max_val=100,
            description="Fast MA window (bars)",
        ),
        ParamSpec(
            "slow_window",
            ParamType.INT,
            default=30,
            required=True,
            min_val=5,
            max_val=500,
            description="Slow MA window (bars)",
        ),
        ParamSpec(
            "ma_type",
            ParamType.STR,
            default="sma",
            choices=["sma", "ema"],
            description="Moving average type: 'sma' (Simple) or 'ema' (Exponential)",
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

    def _calc_ma(self, series: pd.Series, window: int) -> pd.Series:
        """Compute SMA or EMA based on ma_type param."""
        if self.params["ma_type"] == "ema":
            return Indicators.ema(series, window)
        return Indicators.sma(series, window)

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        signals: List[Signal] = []
        asset_type = AssetType(self.params["asset_type"])

        for ticker, df in data.items():
            if len(df) < self.params["slow_window"]:
                continue  # not enough history

            fast_ma = self._calc_ma(df["close"], self.params["fast_window"])
            slow_ma = self._calc_ma(df["close"], self.params["slow_window"])

            cross_above = Indicators.crossover(fast_ma, slow_ma)  # golden cross
            cross_below = Indicators.crossunder(fast_ma, slow_ma)  # dead cross

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
                            "signal": "golden_cross",
                            "ma_type": self.params["ma_type"],
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
                            "signal": "dead_cross",
                            "ma_type": self.params["ma_type"],
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
