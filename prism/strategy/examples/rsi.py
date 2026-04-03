"""
RSI (Relative Strength Index) Strategy

Generates BUY signals when RSI crosses up from oversold territory and
SELL signals when RSI crosses down from overbought territory.

Signal strength is scaled by how far RSI is from the neutral (50) level,
giving stronger conviction to extreme readings.

Usage::

    strategy = RSIStrategy(params={
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
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


class RSIStrategy(Strategy):
    """
    RSI mean-reversion strategy.

    Signals:
        BUY  — RSI rises above the oversold threshold (exit oversold zone)
        SELL — RSI falls below the overbought threshold (exit overbought zone)

    Signal strength is proportional to how extreme the RSI reading was:
        strength = |rsi - 50| / 50   (capped at 1.0)
    """

    param_specs = [
        ParamSpec(
            "rsi_period",
            ParamType.INT,
            default=14,
            min_val=2,
            max_val=100,
            description="RSI look-back period (bars)",
        ),
        ParamSpec(
            "oversold",
            ParamType.FLOAT,
            default=30.0,
            min_val=1.0,
            max_val=49.0,
            description="RSI level below which the asset is considered oversold",
        ),
        ParamSpec(
            "overbought",
            ParamType.FLOAT,
            default=70.0,
            min_val=51.0,
            max_val=99.0,
            description="RSI level above which the asset is considered overbought",
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
        if self.params["oversold"] >= self.params["overbought"]:
            raise ValueError(
                f"oversold ({self.params['oversold']}) must be "
                f"< overbought ({self.params['overbought']})"
            )

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        signals: List[Signal] = []
        asset_type = AssetType(self.params["asset_type"])
        period = self.params["rsi_period"]
        oversold = self.params["oversold"]
        overbought = self.params["overbought"]

        for ticker, df in data.items():
            # Need at least period + 1 bars for RSI and 1 look-back bar
            if len(df) < period + 2:
                continue

            rsi = Indicators.rsi(df["close"], period)

            # Detect crossing out of oversold: previous bar in oversold, current bar above
            prev_rsi = rsi.iloc[-2]
            curr_rsi = rsi.iloc[-1]

            if pd.isna(prev_rsi) or pd.isna(curr_rsi):
                continue

            ts = df.index[-1]
            close_price = float(df["close"].iloc[-1])

            # Strength: how extreme was the reading (distance from neutral 50)
            strength = min(abs(float(curr_rsi) - 50.0) / 50.0, 1.0)
            strength = max(strength, 0.1)  # floor at 0.1 so signal is never trivial

            if prev_rsi <= oversold < curr_rsi:
                # RSI crossed up through oversold threshold → BUY
                signals.append(
                    Signal(
                        timestamp=ts,
                        asset=ticker,
                        asset_type=asset_type,
                        direction=SignalDirection.BUY,
                        strength=strength,
                        price=close_price,
                        meta={
                            "rsi": float(curr_rsi),
                            "rsi_prev": float(prev_rsi),
                            "oversold_threshold": oversold,
                        },
                    )
                )
            elif prev_rsi >= overbought > curr_rsi:
                # RSI crossed down through overbought threshold → SELL
                signals.append(
                    Signal(
                        timestamp=ts,
                        asset=ticker,
                        asset_type=asset_type,
                        direction=SignalDirection.SELL,
                        strength=strength,
                        price=close_price,
                        meta={
                            "rsi": float(curr_rsi),
                            "rsi_prev": float(prev_rsi),
                            "overbought_threshold": overbought,
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
