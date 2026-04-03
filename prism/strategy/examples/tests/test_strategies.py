"""
Unit tests for PRISM strategy implementations:
  - MACrossStrategy (SMA/EMA crossover)
  - RSIStrategy
  - VolumeStrategy (V3 logic)

All tests use synthetic OHLCV data to avoid external dependencies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from prism.strategy.base import SignalDirection
from prism.strategy.examples.ma_cross import MACrossStrategy
from prism.strategy.examples.rsi import RSIStrategy
from prism.strategy.examples.volume import VolumeStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(prices: list[float], volume: float = 1_000.0) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a list of close prices."""
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="1D", tz="UTC")
    closes = pd.Series(prices, index=idx)
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.005,
            "low": closes * 0.995,
            "close": closes,
            "volume": volume,
        },
        index=idx,
    )


def _make_ohlcv_with_volume(
    prices: list[float], volumes: list[float]
) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="1D", tz="UTC")
    closes = pd.Series(prices, index=idx)
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.005,
            "low": closes * 0.995,
            "close": closes,
            "volume": volumes,
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# MACrossStrategy tests
# ---------------------------------------------------------------------------

class TestMACrossStrategy:

    def _cross_buy_data(self, ma_type="sma"):
        """Create data where fast MA crosses above slow MA on the last bar."""
        # Start flat, then spike up sharply so fast > slow on the last bar
        flat = [100.0] * 35
        spike = [110.0, 120.0]
        return _make_ohlcv(flat + spike)

    def test_default_params(self):
        strat = MACrossStrategy(params={"fast_window": 10, "slow_window": 30})
        assert strat.params["ma_type"] == "sma"
        assert strat.params["asset_type"] == "crypto"

    def test_invalid_fast_ge_slow(self):
        with pytest.raises(ValueError, match="fast_window"):
            MACrossStrategy(params={"fast_window": 30, "slow_window": 10})

    def test_invalid_ma_type(self):
        with pytest.raises(ValueError):
            MACrossStrategy(params={"fast_window": 5, "slow_window": 20, "ma_type": "wma"})

    def test_not_enough_history_returns_empty(self):
        strat = MACrossStrategy(params={"fast_window": 5, "slow_window": 30})
        df = _make_ohlcv([100.0] * 10)  # fewer bars than slow_window
        assert strat.generate_signals({"BTC/KRW": df}) == []

    def test_golden_cross_buy_signal_sma(self):
        """Fast SMA crosses above slow SMA on last bar → BUY.

        Price pattern: 20 bars flat at 100, then 4 bars dip to 90,
        then one spike to 200 forces fast SMA above slow SMA on the last bar.
        """
        strat = MACrossStrategy(params={"fast_window": 5, "slow_window": 20, "ma_type": "sma"})
        prices = [100.0] * 20 + [90.0] * 4 + [200.0]
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        buy_signals = [s for s in signals if s.direction == SignalDirection.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].meta["signal"] == "golden_cross"
        assert buy_signals[0].meta["ma_type"] == "sma"

    def test_dead_cross_sell_signal_ema(self):
        """Fast EMA crosses below slow EMA on last bar → SELL.

        Price pattern: 20 bars flat at 100, then 4 bars spike to 110,
        then one crash to 50 forces fast EMA below slow EMA on the last bar.
        """
        strat = MACrossStrategy(params={"fast_window": 5, "slow_window": 20, "ma_type": "ema"})
        prices = [100.0] * 20 + [110.0] * 4 + [50.0]
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        sell_signals = [s for s in signals if s.direction == SignalDirection.SELL]
        assert len(sell_signals) == 1
        assert sell_signals[0].meta["signal"] == "dead_cross"
        assert sell_signals[0].meta["ma_type"] == "ema"

    def test_signal_price_positive(self):
        strat = MACrossStrategy(params={"fast_window": 5, "slow_window": 20, "ma_type": "sma"})
        prices = [100.0 - i * 0.1 for i in range(25)] + [110.0, 115.0]
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        for s in signals:
            assert s.price > 0

    def test_calculate_position_size(self):
        strat = MACrossStrategy(
            params={"fast_window": 5, "slow_window": 20, "position_fraction": 0.05}
        )
        prices = [100.0 - i * 0.1 for i in range(25)] + [110.0, 115.0]
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        if signals:
            ps = strat.calculate_position_size(signals[0], 1_000_000, {})
            assert abs(ps.position_pct - 0.05) < 1e-9


# ---------------------------------------------------------------------------
# RSIStrategy tests
# ---------------------------------------------------------------------------

class TestRSIStrategy:

    def test_default_params(self):
        strat = RSIStrategy()
        assert strat.params["rsi_period"] == 14
        assert strat.params["oversold"] == 30.0
        assert strat.params["overbought"] == 70.0

    def test_invalid_oversold_ge_overbought(self):
        with pytest.raises(ValueError, match="oversold"):
            RSIStrategy(params={"oversold": 70, "overbought": 30})

    def test_not_enough_history_returns_empty(self):
        strat = RSIStrategy(params={"rsi_period": 14})
        df = _make_ohlcv([100.0] * 10)
        assert strat.generate_signals({"BTC/KRW": df}) == []

    def test_buy_signal_on_oversold_exit(self):
        """RSI crossing up through 30 → BUY."""
        strat = RSIStrategy(params={"rsi_period": 5, "oversold": 30.0, "overbought": 70.0})
        # Simulate price drop then sharp recovery
        down = [100.0 - i * 3 for i in range(15)]   # sustained fall → RSI deeply oversold
        up = [down[-1] + 10.0]                         # sharp recovery pushes RSI above 30
        prices = down + up
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        buy_signals = [s for s in signals if s.direction == SignalDirection.BUY]
        assert len(buy_signals) == 1
        assert 0.0 < buy_signals[0].strength <= 1.0

    def test_sell_signal_on_overbought_exit(self):
        """RSI crossing down through 70 → SELL.

        Price pattern: oscillating warm-up (avoids pure-uptrend NaN in EWM RSI),
        followed by a 7-bar rally that drives RSI above 70, then one big drop
        that crosses RSI below 70 on the last bar.
        """
        strat = RSIStrategy(params={"rsi_period": 14, "oversold": 30.0, "overbought": 70.0})
        warmup = [100 + (i % 3 - 1) * 2 for i in range(30)]
        rally = [warmup[-1] + i * 3 for i in range(1, 8)]
        drop_bar = [rally[-1] - 15]
        prices = warmup + rally + drop_bar
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        sell_signals = [s for s in signals if s.direction == SignalDirection.SELL]
        assert len(sell_signals) == 1
        assert 0.0 < sell_signals[0].strength <= 1.0

    def test_no_signal_when_rsi_stays_flat(self):
        """Flat price → RSI near 50, no crossover → no signals."""
        strat = RSIStrategy(params={"rsi_period": 5})
        prices = [100.0] * 30  # perfectly flat
        df = _make_ohlcv(prices)
        signals = strat.generate_signals({"BTC/KRW": df})
        assert signals == []

    def test_signal_meta_contains_rsi(self):
        strat = RSIStrategy(params={"rsi_period": 5, "oversold": 30.0, "overbought": 70.0})
        down = [100.0 - i * 3 for i in range(15)]
        up = [down[-1] + 10.0]
        df = _make_ohlcv(down + up)
        signals = strat.generate_signals({"BTC/KRW": df})
        if signals:
            assert "rsi" in signals[0].meta
            assert "rsi_prev" in signals[0].meta


# ---------------------------------------------------------------------------
# VolumeStrategy tests
# ---------------------------------------------------------------------------

class TestVolumeStrategy:

    def test_default_params(self):
        strat = VolumeStrategy()
        assert strat.params["volume_window"] == 20
        assert strat.params["spike_multiplier"] == 2.0

    def test_not_enough_history_returns_empty(self):
        strat = VolumeStrategy(params={"volume_window": 20})
        prices = [100.0] * 15
        df = _make_ohlcv(prices, volume=1000.0)
        assert strat.generate_signals({"BTC/KRW": df}) == []

    def test_buy_signal_on_volume_spike_bullish(self):
        """Volume spike + bullish candle → BUY."""
        strat = VolumeStrategy(
            params={
                "volume_window": 5,
                "spike_multiplier": 2.0,
                "price_confirm_pct": 0.001,
            }
        )
        n = 10
        prices = [100.0] * n + [105.0]   # last bar moves up 5%
        volumes = [1000.0] * n + [5000.0]  # last bar volume = 5× avg
        df = _make_ohlcv_with_volume(prices, volumes)
        # Make last bar clearly bullish: open < close
        df.loc[df.index[-1], "open"] = 100.5
        signals = strat.generate_signals({"BTC/KRW": df})
        buy_signals = [s for s in signals if s.direction == SignalDirection.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].meta["volume_ratio"] >= 2.0

    def test_sell_signal_on_volume_spike_bearish(self):
        """Volume spike + bearish candle → SELL."""
        strat = VolumeStrategy(
            params={
                "volume_window": 5,
                "spike_multiplier": 2.0,
                "price_confirm_pct": 0.001,
            }
        )
        n = 10
        prices = [100.0] * n + [95.0]    # last bar drops 5%
        volumes = [1000.0] * n + [5000.0]
        df = _make_ohlcv_with_volume(prices, volumes)
        df.loc[df.index[-1], "open"] = 99.5   # open > close → bearish
        signals = strat.generate_signals({"BTC/KRW": df})
        sell_signals = [s for s in signals if s.direction == SignalDirection.SELL]
        assert len(sell_signals) == 1

    def test_no_signal_without_volume_spike(self):
        """No volume spike → no signal even if price moves."""
        strat = VolumeStrategy(
            params={
                "volume_window": 5,
                "spike_multiplier": 3.0,
                "price_confirm_pct": 0.001,
            }
        )
        n = 10
        prices = [100.0] * n + [105.0]
        volumes = [1000.0] * (n + 1)  # flat volume, no spike
        df = _make_ohlcv_with_volume(prices, volumes)
        assert strat.generate_signals({"BTC/KRW": df}) == []

    def test_no_signal_without_price_confirmation(self):
        """Volume spike but price barely moves → no signal (below confirm_pct)."""
        strat = VolumeStrategy(
            params={
                "volume_window": 5,
                "spike_multiplier": 2.0,
                "price_confirm_pct": 0.05,  # require 5% move
            }
        )
        n = 10
        prices = [100.0] * n + [100.1]   # only 0.1% move
        volumes = [1000.0] * n + [5000.0]
        df = _make_ohlcv_with_volume(prices, volumes)
        assert strat.generate_signals({"BTC/KRW": df}) == []

    def test_strength_bounded(self):
        strat = VolumeStrategy(
            params={"volume_window": 5, "spike_multiplier": 2.0, "price_confirm_pct": 0.001}
        )
        n = 10
        prices = [100.0] * n + [110.0]
        volumes = [1000.0] * n + [100_000.0]  # enormous spike
        df = _make_ohlcv_with_volume(prices, volumes)
        df.loc[df.index[-1], "open"] = 101.0
        signals = strat.generate_signals({"BTC/KRW": df})
        for s in signals:
            assert 0.0 < s.strength <= 1.0

    def test_calculate_position_size(self):
        strat = VolumeStrategy(
            params={
                "volume_window": 5,
                "spike_multiplier": 2.0,
                "price_confirm_pct": 0.001,
                "position_fraction": 0.20,
            }
        )
        n = 10
        prices = [100.0] * n + [105.0]
        volumes = [1000.0] * n + [5000.0]
        df = _make_ohlcv_with_volume(prices, volumes)
        df.loc[df.index[-1], "open"] = 100.5
        signals = strat.generate_signals({"BTC/KRW": df})
        if signals:
            ps = strat.calculate_position_size(signals[0], 1_000_000, {})
            assert ps.notional_value > 0
            assert ps.quantity > 0
