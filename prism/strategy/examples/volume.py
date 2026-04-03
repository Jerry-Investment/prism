"""
Volume-Based Strategy (V3 Logic)

Generates BUY signals when a volume spike accompanies upward price
momentum, and SELL signals when a volume spike accompanies downward
price momentum.

This mirrors the V3 strategy logic that achieved Sharpe 2.09 on
Upbit BTC/KRW paper trading.

Core rules:
  - Volume spike: current volume > volume_ma * spike_multiplier
  - Price direction (BUY):  close > open  AND  close > prev_close
  - Price direction (SELL): close < open  AND  close < prev_close

Signal strength scales with the volume ratio (how strong the spike is).

Usage::

    strategy = VolumeStrategy(params={
        "volume_window": 20,
        "spike_multiplier": 2.0,
        "price_confirm_pct": 0.002,   # require 0.2% move to avoid noise
    })
    signals = strategy.generate_signals({"BTC/KRW": ohlcv_df})
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from prism.strategy.base import AssetType, Signal, SignalDirection, Strategy
from prism.strategy.indicators import Indicators
from prism.strategy.params import ParamSpec, ParamType
from prism.strategy.sizing import FixedFractionSizer, PositionSize


class VolumeStrategy(Strategy):
    """
    Volume spike + price direction confirmation strategy.

    Replicates the V3 strategy logic (Sharpe 2.09, Win Rate 67%,
    Max DD 0.0% on Upbit BTC/KRW paper trading).

    Signals:
        BUY  — volume spike + bullish candle (close > open AND close > prev_close)
        SELL — volume spike + bearish candle (close < open AND close < prev_close)

    Signal strength = min(volume_ratio / (spike_multiplier * 2), 1.0)
    where volume_ratio = current_volume / rolling_volume_ma
    """

    param_specs = [
        ParamSpec(
            "volume_window",
            ParamType.INT,
            default=20,
            min_val=5,
            max_val=200,
            description="Rolling window for average volume baseline (bars)",
        ),
        ParamSpec(
            "spike_multiplier",
            ParamType.FLOAT,
            default=2.0,
            min_val=1.1,
            max_val=10.0,
            description="Volume must exceed volume_ma * spike_multiplier to qualify",
        ),
        ParamSpec(
            "price_confirm_pct",
            ParamType.FLOAT,
            default=0.002,
            min_val=0.0,
            max_val=0.05,
            description=(
                "Minimum price move (as fraction of close) required for"
                " direction confirmation, e.g. 0.002 = 0.2%"
            ),
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

    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        signals: List[Signal] = []
        asset_type = AssetType(self.params["asset_type"])
        vol_window = self.params["volume_window"]
        spike_mult = self.params["spike_multiplier"]
        confirm_pct = self.params["price_confirm_pct"]

        for ticker, df in data.items():
            if len(df) < vol_window + 1:
                continue

            volume_ma = Indicators.sma(df["volume"], vol_window)

            last = df.iloc[-1]
            ts = df.index[-1]

            curr_vol = float(last["volume"])
            curr_vol_ma = float(volume_ma.iloc[-1])

            if curr_vol_ma <= 0 or pd.isna(curr_vol_ma):
                continue

            volume_ratio = curr_vol / curr_vol_ma
            is_spike = volume_ratio >= spike_mult

            if not is_spike:
                continue

            close = float(last["close"])
            open_ = float(last["open"])
            prev_close = float(df["close"].iloc[-2])

            # Price direction confirmation
            close_vs_open = (close - open_) / open_ if open_ > 0 else 0.0
            close_vs_prev = (close - prev_close) / prev_close if prev_close > 0 else 0.0

            is_bullish = close_vs_open > confirm_pct and close_vs_prev > confirm_pct
            is_bearish = close_vs_open < -confirm_pct and close_vs_prev < -confirm_pct

            if not is_bullish and not is_bearish:
                continue

            # Strength: volume ratio normalised, capped at 1.0
            strength = min(volume_ratio / (spike_mult * 2.0), 1.0)
            strength = max(strength, 0.1)

            direction = SignalDirection.BUY if is_bullish else SignalDirection.SELL

            signals.append(
                Signal(
                    timestamp=ts,
                    asset=ticker,
                    asset_type=asset_type,
                    direction=direction,
                    strength=strength,
                    price=close,
                    meta={
                        "volume_ratio": round(volume_ratio, 4),
                        "volume_ma": round(curr_vol_ma, 2),
                        "close_vs_open_pct": round(close_vs_open * 100, 4),
                        "close_vs_prev_pct": round(close_vs_prev * 100, 4),
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
