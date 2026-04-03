"""
PRISM Built-in Indicator Library

All indicators accept a pandas Series (or DataFrame where noted) and return
a pandas Series with the same index.  They are pure functions — no hidden state.

Included:
  Moving Averages  : sma, ema, wma
  Momentum         : rsi, macd, macd_signal, macd_hist
  Volatility       : bollinger_bands, atr
  Volume           : volume_profile, obv, vwap
  Utility          : crossover, crossunder
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


class Indicators:
    """Namespace for all built-in technical indicators."""

    # ------------------------------------------------------------------
    # Moving Averages
    # ------------------------------------------------------------------

    @staticmethod
    def sma(series: pd.Series, window: int) -> pd.Series:
        """Simple Moving Average."""
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        return series.rolling(window=window, min_periods=window).mean()

    @staticmethod
    def ema(series: pd.Series, span: int) -> pd.Series:
        """Exponential Moving Average (com = span-1 / Wilder-style adjust=False)."""
        if span < 1:
            raise ValueError(f"span must be >= 1, got {span}")
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def wma(series: pd.Series, window: int) -> pd.Series:
        """Weighted Moving Average (linear weights, most-recent has highest weight)."""
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        weights = np.arange(1, window + 1, dtype=float)

        def _wma(x: np.ndarray) -> float:
            if np.isnan(x).any():
                return np.nan
            return float(np.dot(x, weights) / weights.sum())

        return series.rolling(window=window, min_periods=window).apply(_wma, raw=True)

    # ------------------------------------------------------------------
    # Momentum
    # ------------------------------------------------------------------

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (Wilder smoothing).

        Returns values in [0, 100].
        """
        if period < 2:
            raise ValueError(f"period must be >= 2, got {period}")
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_val = 100.0 - (100.0 / (1.0 + rs))
        return rsi_val.rename("rsi")

    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD indicator.

        Returns:
            (macd_line, signal_line, histogram)
            - macd_line  = EMA(fast) - EMA(slow)
            - signal_line = EMA(macd_line, signal)
            - histogram   = macd_line - signal_line
        """
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be < slow ({slow})")
        ema_fast = Indicators.ema(series, fast)
        ema_slow = Indicators.ema(series, slow)
        macd_line = (ema_fast - ema_slow).rename("macd")
        signal_line = Indicators.ema(macd_line, signal).rename("macd_signal")
        histogram = (macd_line - signal_line).rename("macd_hist")
        return macd_line, signal_line, histogram

    # ------------------------------------------------------------------
    # Volatility
    # ------------------------------------------------------------------

    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        window: int = 20,
        num_std: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.

        Returns:
            (upper, middle, lower)
            - middle = SMA(window)
            - upper  = middle + num_std * rolling_std
            - lower  = middle - num_std * rolling_std
        """
        middle = Indicators.sma(series, window).rename("bb_middle")
        std = series.rolling(window=window, min_periods=window).std()
        upper = (middle + num_std * std).rename("bb_upper")
        lower = (middle - num_std * std).rename("bb_lower")
        return upper, middle, lower

    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Average True Range (Wilder smoothing)."""
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.ewm(com=period - 1, adjust=False).mean().rename("atr")

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    @staticmethod
    def volume_profile(
        close: pd.Series,
        volume: pd.Series,
        bins: int = 20,
    ) -> pd.DataFrame:
        """
        Volume Profile: distributes total traded volume across price levels.

        Returns a DataFrame with columns:
            price_low, price_high, volume  (one row per price bucket)

        Useful for identifying high-volume nodes (support/resistance).
        """
        if len(close) < bins:
            raise ValueError(
                f"Need at least {bins} data points for volume_profile, got {len(close)}"
            )
        price_min = close.min()
        price_max = close.max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        indices = np.digitize(close.values, bin_edges, right=True)
        indices = np.clip(indices, 1, bins)  # keep inside [1, bins]

        vol_by_bin = np.zeros(bins)
        for i, vol in zip(indices, volume.values):
            vol_by_bin[i - 1] += vol

        return pd.DataFrame(
            {
                "price_low": bin_edges[:-1],
                "price_high": bin_edges[1:],
                "volume": vol_by_bin,
            }
        )

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume."""
        direction = np.sign(close.diff()).fillna(0)
        return (direction * volume).cumsum().rename("obv")

    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> pd.Series:
        """
        Volume Weighted Average Price.

        Uses typical price = (high + low + close) / 3.
        Resets at the start of the series (no intraday grouping here;
        the caller should slice to the desired session window first).
        """
        typical = (high + low + close) / 3.0
        cum_tp_vol = (typical * volume).cumsum()
        cum_vol = volume.cumsum()
        return (cum_tp_vol / cum_vol).rename("vwap")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
        """
        Returns True on bars where series_a crosses above series_b.
        i.e. previous bar: a < b, current bar: a >= b.
        """
        prev_a = series_a.shift(1)
        prev_b = series_b.shift(1)
        return ((prev_a < prev_b) & (series_a >= series_b)).rename("crossover")

    @staticmethod
    def crossunder(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
        """
        Returns True on bars where series_a crosses below series_b.
        i.e. previous bar: a > b, current bar: a <= b.
        """
        prev_a = series_a.shift(1)
        prev_b = series_b.shift(1)
        return ((prev_a > prev_b) & (series_a <= series_b)).rename("crossunder")
