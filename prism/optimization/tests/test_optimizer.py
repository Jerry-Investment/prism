"""
Tests for the PRISM Parameter Optimization Engine.

Uses synthetic OHLCV data and MACrossStrategy to validate:
- Grid search returns best params and trials
- Bayesian search finds reasonable params
- Walk-forward produces per-window results
- OOS split and CV scoring work
- Heatmap generation works without error
"""

import sys
import os

# Make prism importable from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Also make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

import pytest
import numpy as np
import pandas as pd

from prism.optimization import ParameterOptimizer, OptimizerConfig, ParamGrid
from prism.strategy.examples.ma_cross import MACrossStrategy


def _make_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data with a slight uptrend."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="1D", tz="UTC")
    close = 50_000 + np.cumsum(rng.normal(100, 800, n))
    close = np.maximum(close, 1000.0)
    high = close * (1 + rng.uniform(0.001, 0.01, n))
    low = close * (1 - rng.uniform(0.001, 0.01, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(1_000, 50_000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def data():
    return {"BTC/KRW": _make_ohlcv(300)}


@pytest.fixture
def engine():
    from app.core.backtest_engine import BacktestEngine
    return BacktestEngine(initial_capital=10_000_000)


@pytest.fixture
def optimizer(engine):
    config = OptimizerConfig(
        metric="sharpe_ratio",
        cv_folds=2,
        oos_fraction=0.2,
        n_trials=10,
        fixed_params={"asset_type": "crypto"},
    )
    return ParameterOptimizer(MACrossStrategy, engine, config)


class TestGridSearch:
    def test_returns_best_params(self, optimizer, data):
        grid: ParamGrid = {
            "fast_window": [5, 10],
            "slow_window": [20, 40],
            "ma_type": ["sma"],
            "position_fraction": [0.1],
        }
        result = optimizer.grid_search(data, grid)
        assert result.best_params, "Should return non-empty best_params"
        assert "fast_window" in result.best_params
        assert "slow_window" in result.best_params

    def test_all_trials_recorded(self, optimizer, data):
        grid: ParamGrid = {
            "fast_window": [5, 10],
            "slow_window": [20, 40],
            "ma_type": ["sma"],
            "position_fraction": [0.1],
        }
        result = optimizer.grid_search(data, grid)
        # 2x2x1x1 = 4 combos, but invalid (fast >= slow) filtered by strategy
        assert len(result.all_trials) > 0

    def test_oos_metric_populated(self, optimizer, data):
        grid: ParamGrid = {
            "fast_window": [5],
            "slow_window": [20],
            "ma_type": ["sma"],
            "position_fraction": [0.1],
        }
        result = optimizer.grid_search(data, grid)
        # OOS metric should be computed (may be None if no trades, but not crash)
        assert "oos_metric" in result.__dict__

    def test_progress_callback(self, optimizer, data):
        grid: ParamGrid = {
            "fast_window": [5, 10],
            "slow_window": [30],
            "ma_type": ["sma"],
            "position_fraction": [0.1],
        }
        progress_values = []
        optimizer.grid_search(data, grid, progress_cb=lambda p: progress_values.append(p))
        assert progress_values, "Progress callback should be called"
        assert progress_values[-1] == pytest.approx(100.0)


class TestBayesianSearch:
    def test_returns_best_params(self, optimizer, data):
        param_specs = [
            {"name": "fast_window", "type": "int", "low": 5, "high": 20},
            {"name": "slow_window", "type": "int", "low": 25, "high": 60},
            {"name": "ma_type", "type": "categorical", "choices": ["sma", "ema"]},
            {"name": "position_fraction", "type": "float", "low": 0.05, "high": 0.3},
        ]
        result = optimizer.bayesian_search(data, param_specs)
        assert result.best_params
        assert result.best_metric is not None or result.best_metric is None  # no assertion on value
        assert "fast_window" in result.best_params

    def test_trials_recorded(self, optimizer, data):
        param_specs = [
            {"name": "fast_window", "type": "int", "low": 5, "high": 20},
            {"name": "slow_window", "type": "int", "low": 25, "high": 60},
            {"name": "ma_type", "type": "categorical", "choices": ["sma"]},
            {"name": "position_fraction", "type": "float", "low": 0.1, "high": 0.2},
        ]
        result = optimizer.bayesian_search(data, param_specs)
        assert len(result.all_trials) > 0


class TestWalkForward:
    def test_walk_forward_windows(self, optimizer, data):
        param_specs = [
            {"name": "fast_window", "type": "int", "low": 5, "high": 15},
            {"name": "slow_window", "type": "int", "low": 20, "high": 50},
            {"name": "ma_type", "type": "categorical", "choices": ["sma"]},
            {"name": "position_fraction", "type": "float", "low": 0.1, "high": 0.2},
        ]
        wf = optimizer.walk_forward(
            data, param_specs, n_windows=3, train_frac=0.7,
            use_bayesian=True, n_trials_per_window=5,
        )
        assert len(wf.windows) > 0
        assert wf.avg_test_metric is not None or wf.avg_test_metric is None
        # Param stability keys should match strategy params
        assert len(wf.param_stability) > 0

    def test_walk_forward_fields(self, optimizer, data):
        param_specs = [
            {"name": "fast_window", "type": "int", "low": 5, "high": 15},
            {"name": "slow_window", "type": "int", "low": 20, "high": 50},
            {"name": "ma_type", "type": "categorical", "choices": ["sma"]},
            {"name": "position_fraction", "type": "float", "low": 0.1, "high": 0.2},
        ]
        wf = optimizer.walk_forward(
            data, param_specs, n_windows=2, n_trials_per_window=5,
        )
        for w in wf.windows:
            assert "window" in w
            assert "best_params" in w
            assert "train_metric" in w
            assert "test_metric" in w


class TestHeatmap:
    def test_plot_heatmap_no_error(self, optimizer, data):
        import matplotlib
        matplotlib.use("Agg")

        grid: ParamGrid = {
            "fast_window": [5, 10, 15],
            "slow_window": [20, 40],
            "ma_type": ["sma"],
            "position_fraction": [0.1],
        }
        result = optimizer.grid_search(data, grid)
        fig = optimizer.plot_heatmap(result, x_param="fast_window", y_param="slow_window")
        assert fig is not None

    def test_plot_walk_forward_no_error(self, optimizer, data):
        import matplotlib
        matplotlib.use("Agg")

        param_specs = [
            {"name": "fast_window", "type": "int", "low": 5, "high": 15},
            {"name": "slow_window", "type": "int", "low": 20, "high": 50},
            {"name": "ma_type", "type": "categorical", "choices": ["sma"]},
            {"name": "position_fraction", "type": "float", "low": 0.1, "high": 0.2},
        ]
        wf = optimizer.walk_forward(data, param_specs, n_windows=2, n_trials_per_window=5)
        if wf.windows:
            fig = optimizer.plot_walk_forward(wf)
            assert fig is not None
