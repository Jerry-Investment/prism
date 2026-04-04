"""
PRISM Parameter Optimization Engine — Phase 3

Supports:
  - Grid Search (exhaustive)
  - Bayesian Optimization via Optuna
  - Walk-Forward Optimization (rolling window)
  - Overfitting safeguards: k-fold time-series cross-validation, OOS testing
  - Heatmap visualization of optimization surfaces

Usage::

    from prism.optimization import ParameterOptimizer, OptimizerConfig, ParamGrid
    from prism.strategy.examples.ma_cross import MACrossStrategy
    from backend.app.core.backtest_engine import BacktestEngine

    grid = ParamGrid({
        "fast_window": list(range(5, 30, 5)),
        "slow_window": list(range(20, 100, 10)),
        "ma_type": ["sma", "ema"],
    })
    config = OptimizerConfig(
        metric="sharpe_ratio",
        n_trials=100,           # for Bayesian
        cv_folds=3,
        oos_fraction=0.2,
    )
    optimizer = ParameterOptimizer(
        strategy_class=MACrossStrategy,
        engine=BacktestEngine(),
        config=config,
    )
    result = optimizer.grid_search(data, grid)
    print(result.best_params, result.best_metric)
"""

from __future__ import annotations

import copy
import itertools
import logging
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

ParamGrid = Dict[str, List[Any]]
"""Mapping of parameter name → list of candidate values."""


@dataclass
class OptimizationResult:
    """Result of a single optimization run (grid or Bayesian)."""

    best_params: Dict[str, Any]
    best_metric: float
    metric_name: str
    all_trials: List[Dict[str, Any]] = field(default_factory=list)
    """Each entry: {params, in_sample_metric, oos_metric, cv_mean, cv_std}"""
    oos_metric: Optional[float] = None
    cv_mean: Optional[float] = None
    cv_std: Optional[float] = None


@dataclass
class WalkForwardResult:
    """Result of a walk-forward optimization."""

    windows: List[Dict[str, Any]] = field(default_factory=list)
    """Each entry: {train_start, train_end, test_start, test_end, best_params, train_metric, test_metric}"""
    avg_test_metric: Optional[float] = None
    param_stability: Dict[str, Any] = field(default_factory=dict)
    """Describes how stable each parameter was across windows (mean, std, mode)."""


@dataclass
class OptimizerConfig:
    """Configuration for the parameter optimizer."""

    metric: str = "sharpe_ratio"
    """Optimization target. One of: sharpe_ratio, sortino_ratio, total_return,
    win_rate, profit_factor. Higher is always better."""

    n_trials: int = 100
    """Number of trials for Bayesian optimization."""

    cv_folds: int = 3
    """Number of time-series CV folds (walk-forward splits within training data)."""

    oos_fraction: float = 0.2
    """Fraction of data to reserve as out-of-sample test set (0 to disable)."""

    n_jobs: int = 1
    """Parallel jobs for grid search (1 = serial). Note: Optuna manages its own."""

    optuna_timeout: Optional[float] = None
    """Hard timeout (seconds) for Optuna studies. None = no timeout."""

    higher_is_better: bool = True
    """Direction of optimization. Always True for our standard metrics."""

    fixed_params: Dict[str, Any] = field(default_factory=dict)
    """Parameters to fix (not optimize). Merged into every trial."""


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------


class ParameterOptimizer:
    """
    Unified parameter optimization engine for PRISM strategies.

    Args:
        strategy_class: The Strategy subclass (not an instance).
        engine:         A configured BacktestEngine instance.
        config:         OptimizerConfig with metric and search settings.
    """

    def __init__(
        self,
        strategy_class: Type,
        engine: Any,  # BacktestEngine — avoid circular import
        config: Optional[OptimizerConfig] = None,
    ) -> None:
        self.strategy_class = strategy_class
        self.engine = engine
        self.config = config or OptimizerConfig()

    # ------------------------------------------------------------------
    # Public: Grid Search
    # ------------------------------------------------------------------

    def grid_search(
        self,
        data: Dict[str, pd.DataFrame],
        grid: ParamGrid,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> OptimizationResult:
        """
        Exhaustive grid search over all parameter combinations.

        Args:
            data:        Symbol → OHLCV DataFrame (full dataset).
            grid:        Mapping of param name → list of values to try.
            progress_cb: Optional callback receiving progress pct in [0, 100].

        Returns:
            OptimizationResult with best_params and per-trial records.
        """
        train_data, oos_data = self._split_oos(data)

        keys = list(grid.keys())
        values = list(grid.values())
        combos = list(itertools.product(*values))
        n = len(combos)

        all_trials: List[Dict[str, Any]] = []
        best_metric = float("-inf")
        best_params: Dict[str, Any] = {}

        for i, combo in enumerate(combos):
            params = dict(zip(keys, combo))
            params.update(self.config.fixed_params)

            trial = self._evaluate_params(params, train_data)
            all_trials.append(trial)

            if trial["in_sample_metric"] is not None and trial["in_sample_metric"] > best_metric:
                best_metric = trial["in_sample_metric"]
                best_params = params

            if progress_cb and n > 0:
                progress_cb((i + 1) / n * 100.0)

        # OOS evaluation of best params
        oos_metric = None
        if oos_data is not None and best_params:
            oos_metric = self._run_backtest_metric(best_params, oos_data)

        return OptimizationResult(
            best_params=best_params,
            best_metric=best_metric,
            metric_name=self.config.metric,
            all_trials=all_trials,
            oos_metric=oos_metric,
        )

    # ------------------------------------------------------------------
    # Public: Bayesian Optimization
    # ------------------------------------------------------------------

    def bayesian_search(
        self,
        data: Dict[str, pd.DataFrame],
        param_specs: List[Dict[str, Any]],
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> OptimizationResult:
        """
        Bayesian optimization using Optuna.

        Args:
            data:         Symbol → OHLCV DataFrame (full dataset).
            param_specs:  List of parameter spec dicts. Each dict must have:
                          - name (str)
                          - type: "int" | "float" | "categorical"
                          - low/high for int/float, or choices for categorical
                          - Optional: step (int/float), log (bool)
            progress_cb:  Optional callback receiving pct in [0, 100].

        Returns:
            OptimizationResult with best_params and trial history.

        Example param_specs::

            [
                {"name": "fast_window", "type": "int", "low": 2, "high": 50},
                {"name": "slow_window", "type": "int", "low": 10, "high": 200},
                {"name": "ma_type", "type": "categorical", "choices": ["sma", "ema"]},
            ]
        """
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        train_data, oos_data = self._split_oos(data)
        all_trials: List[Dict[str, Any]] = []
        completed = [0]

        def objective(trial: "optuna.Trial") -> float:
            params = self._suggest_params(trial, param_specs)
            params.update(self.config.fixed_params)

            metric = self._run_backtest_metric(params, train_data)
            if metric is None:
                return float("-inf")

            cv_mean, cv_std = self._cv_score(params, train_data)
            all_trials.append({
                "params": params,
                "in_sample_metric": metric,
                "cv_mean": cv_mean,
                "cv_std": cv_std,
                "oos_metric": None,
            })

            completed[0] += 1
            if progress_cb:
                progress_cb(min(completed[0] / self.config.n_trials * 100.0, 99.0))

            return metric

        direction = "maximize" if self.config.higher_is_better else "minimize"
        study = optuna.create_study(direction=direction)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            study.optimize(
                objective,
                n_trials=self.config.n_trials,
                timeout=self.config.optuna_timeout,
                n_jobs=self.config.n_jobs,
            )

        best_params = dict(study.best_params)
        best_params.update(self.config.fixed_params)
        best_metric = study.best_value

        # OOS evaluation
        oos_metric = None
        if oos_data is not None:
            oos_metric = self._run_backtest_metric(best_params, oos_data)

        # CV on best params
        cv_mean, cv_std = self._cv_score(best_params, train_data)

        if progress_cb:
            progress_cb(100.0)

        return OptimizationResult(
            best_params=best_params,
            best_metric=best_metric,
            metric_name=self.config.metric,
            all_trials=all_trials,
            oos_metric=oos_metric,
            cv_mean=cv_mean,
            cv_std=cv_std,
        )

    # ------------------------------------------------------------------
    # Public: Walk-Forward Optimization
    # ------------------------------------------------------------------

    def walk_forward(
        self,
        data: Dict[str, pd.DataFrame],
        param_specs: List[Dict[str, Any]],
        n_windows: int = 5,
        train_frac: float = 0.7,
        use_bayesian: bool = True,
        n_trials_per_window: int = 50,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> WalkForwardResult:
        """
        Walk-forward optimization: repeatedly train on a window and test on the next.

        Args:
            data:                 Symbol → OHLCV DataFrame.
            param_specs:          Parameter specs for Bayesian search (or grid keys).
            n_windows:            Number of walk-forward windows.
            train_frac:           Fraction of each window used for training.
            use_bayesian:         If True, use Bayesian per window; else grid search.
            n_trials_per_window:  Optuna trials per window.
            progress_cb:          Optional progress callback.

        Returns:
            WalkForwardResult with per-window stats and parameter stability info.
        """
        # Align all symbols to a common time index
        common_idx = self._common_index(data)
        n = len(common_idx)
        if n < n_windows * 10:
            raise ValueError(f"Not enough data ({n} bars) for {n_windows} walk-forward windows.")

        window_size = n // n_windows
        windows_result: List[Dict[str, Any]] = []
        all_best_params: List[Dict[str, Any]] = []

        for w in range(n_windows):
            start_idx = w * window_size
            end_idx = start_idx + window_size if w < n_windows - 1 else n
            split_idx = start_idx + int((end_idx - start_idx) * train_frac)

            train_ts = common_idx[start_idx:split_idx]
            test_ts = common_idx[split_idx:end_idx]

            if len(train_ts) < 10 or len(test_ts) < 5:
                continue

            train_data = {sym: df.loc[df.index.isin(train_ts)] for sym, df in data.items()}
            test_data = {sym: df.loc[df.index.isin(test_ts)] for sym, df in data.items()}

            # Remove empty slices
            train_data = {k: v for k, v in train_data.items() if not v.empty}
            test_data = {k: v for k, v in test_data.items() if not v.empty}

            if not train_data or not test_data:
                continue

            # Optimize on training window
            win_config = copy.copy(self.config)
            win_config.n_trials = n_trials_per_window
            win_config.oos_fraction = 0.0  # no nested OOS inside WF windows
            win_optimizer = ParameterOptimizer(self.strategy_class, self.engine, win_config)

            if use_bayesian:
                win_result = win_optimizer.bayesian_search(train_data, param_specs)
            else:
                # Build grid from param_specs
                grid = {
                    spec["name"]: list(range(spec["low"], spec["high"] + 1, spec.get("step", 1)))
                    if spec["type"] in ("int", "float")
                    else spec["choices"]
                    for spec in param_specs
                }
                win_result = win_optimizer.grid_search(train_data, grid)

            best_params = win_result.best_params
            all_best_params.append(best_params)

            train_metric = win_result.best_metric
            test_metric = self._run_backtest_metric(best_params, test_data)

            windows_result.append({
                "window": w + 1,
                "train_start": train_ts[0].isoformat() if hasattr(train_ts[0], "isoformat") else str(train_ts[0]),
                "train_end": train_ts[-1].isoformat() if hasattr(train_ts[-1], "isoformat") else str(train_ts[-1]),
                "test_start": test_ts[0].isoformat() if hasattr(test_ts[0], "isoformat") else str(test_ts[0]),
                "test_end": test_ts[-1].isoformat() if hasattr(test_ts[-1], "isoformat") else str(test_ts[-1]),
                "best_params": best_params,
                "train_metric": train_metric,
                "test_metric": test_metric,
            })

            if progress_cb:
                progress_cb((w + 1) / n_windows * 100.0)

        test_metrics = [w["test_metric"] for w in windows_result if w["test_metric"] is not None]
        avg_test = sum(test_metrics) / len(test_metrics) if test_metrics else None

        param_stability = self._compute_param_stability(all_best_params)

        return WalkForwardResult(
            windows=windows_result,
            avg_test_metric=avg_test,
            param_stability=param_stability,
        )

    # ------------------------------------------------------------------
    # Public: Visualization
    # ------------------------------------------------------------------

    def plot_heatmap(
        self,
        result: OptimizationResult,
        x_param: str,
        y_param: str,
        output_path: Optional[str] = None,
    ) -> "plt.Figure":
        """
        Plot a 2D parameter heatmap from an optimization result.

        Args:
            result:      OptimizationResult from grid_search or bayesian_search.
            x_param:     Parameter name for the x-axis.
            y_param:     Parameter name for the y-axis.
            output_path: If given, save the figure to this path (PNG/PDF).

        Returns:
            matplotlib Figure object.
        """
        import matplotlib.pyplot as plt
        import seaborn as sns

        trials = result.all_trials
        if not trials:
            raise ValueError("No trials found in OptimizationResult.")

        x_vals = sorted(set(t["params"][x_param] for t in trials if x_param in t["params"]))
        y_vals = sorted(set(t["params"][y_param] for t in trials if y_param in t["params"]))

        # Build metric matrix
        matrix = pd.DataFrame(index=y_vals, columns=x_vals, dtype=float)
        for trial in trials:
            p = trial["params"]
            if x_param not in p or y_param not in p:
                continue
            val = trial.get("in_sample_metric")
            if val is not None:
                existing = matrix.at[p[y_param], p[x_param]]
                if pd.isna(existing) or val > existing:
                    matrix.at[p[y_param], p[x_param]] = val

        fig, ax = plt.subplots(figsize=(10, 7))
        sns.heatmap(
            matrix.astype(float),
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            ax=ax,
            linewidths=0.5,
            cbar_kws={"label": self.config.metric},
        )
        ax.set_title(
            f"Parameter Optimization Heatmap\n{self.config.metric} ({x_param} vs {y_param})"
        )
        ax.set_xlabel(x_param)
        ax.set_ylabel(y_param)
        plt.tight_layout()

        if output_path:
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info("Heatmap saved to %s", output_path)

        return fig

    def plot_walk_forward(
        self,
        wf_result: WalkForwardResult,
        output_path: Optional[str] = None,
    ) -> "plt.Figure":
        """
        Bar chart comparing train vs test metric across walk-forward windows.

        Args:
            wf_result:   WalkForwardResult from walk_forward().
            output_path: If given, save the figure to this path.

        Returns:
            matplotlib Figure object.
        """
        import matplotlib.pyplot as plt

        windows = wf_result.windows
        if not windows:
            raise ValueError("No walk-forward windows found.")

        labels = [f"W{w['window']}" for w in windows]
        train_vals = [w["train_metric"] if w["train_metric"] is not None else 0.0 for w in windows]
        test_vals = [w["test_metric"] if w["test_metric"] is not None else 0.0 for w in windows]

        x = range(len(labels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar([xi - width / 2 for xi in x], train_vals, width, label="Train", color="steelblue")
        ax.bar([xi + width / 2 for xi in x], test_vals, width, label="Test", color="coral")

        if wf_result.avg_test_metric is not None:
            ax.axhline(wf_result.avg_test_metric, color="darkred", linestyle="--",
                       label=f"Avg Test: {wf_result.avg_test_metric:.3f}")

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.set_ylabel(self.config.metric)
        ax.set_title("Walk-Forward Optimization — Train vs Test Performance")
        ax.legend()
        plt.tight_layout()

        if output_path:
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info("Walk-forward chart saved to %s", output_path)

        return fig

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_oos(
        self,
        data: Dict[str, pd.DataFrame],
    ) -> Tuple[Dict[str, pd.DataFrame], Optional[Dict[str, pd.DataFrame]]]:
        """Split data into train/OOS portions based on config.oos_fraction."""
        if self.config.oos_fraction <= 0:
            return data, None

        common_idx = self._common_index(data)
        split = int(len(common_idx) * (1 - self.config.oos_fraction))
        train_ts = common_idx[:split]
        oos_ts = common_idx[split:]

        train = {sym: df.loc[df.index.isin(train_ts)] for sym, df in data.items()}
        oos = {sym: df.loc[df.index.isin(oos_ts)] for sym, df in data.items()}
        train = {k: v for k, v in train.items() if not v.empty}
        oos = {k: v for k, v in oos.items() if not v.empty}

        return train, oos if oos else None

    def _common_index(self, data: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Return the union of all symbol timestamp indices, sorted."""
        all_ts = sorted(set().union(*[df.index.tolist() for df in data.values()]))
        return pd.DatetimeIndex(all_ts)

    def _run_backtest_metric(
        self,
        params: Dict[str, Any],
        data: Dict[str, pd.DataFrame],
    ) -> Optional[float]:
        """Instantiate strategy, run backtest, return the configured metric."""
        try:
            strategy = self.strategy_class(params=copy.deepcopy(params))
            result = self.engine.run(strategy, data)
            return self._extract_metric(result)
        except Exception as exc:
            logger.debug("Trial failed for params %s: %s", params, exc)
            return None

    def _extract_metric(self, result: Any) -> Optional[float]:
        """Extract the target metric from a BacktestResult."""
        metric = self.config.metric
        val = getattr(result, metric, None)
        if val is None:
            return None
        if not isinstance(val, (int, float)):
            return None
        import math
        return val if not math.isnan(val) else None

    def _evaluate_params(
        self,
        params: Dict[str, Any],
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, Any]:
        """Run backtest + optional CV for one param set. Returns trial dict."""
        in_sample = self._run_backtest_metric(params, data)
        cv_mean, cv_std = None, None
        if in_sample is not None and self.config.cv_folds > 1:
            cv_mean, cv_std = self._cv_score(params, data)
        return {
            "params": params,
            "in_sample_metric": in_sample,
            "cv_mean": cv_mean,
            "cv_std": cv_std,
            "oos_metric": None,
        }

    def _cv_score(
        self,
        params: Dict[str, Any],
        data: Dict[str, pd.DataFrame],
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Time-series k-fold cross-validation.

        Splits the training data into k non-overlapping folds in order,
        trains (uses earlier data) and tests on the fold.
        Returns (mean_metric, std_metric).
        """
        k = self.config.cv_folds
        common_idx = self._common_index(data)
        n = len(common_idx)
        if n < k * 5:
            return None, None

        fold_size = n // (k + 1)
        scores: List[float] = []

        for i in range(1, k + 1):
            train_end = i * fold_size
            test_start = train_end
            test_end = test_start + fold_size

            if test_end > n:
                break

            train_ts = common_idx[:train_end]
            test_ts = common_idx[test_start:test_end]

            fold_train = {sym: df.loc[df.index.isin(train_ts)] for sym, df in data.items()}
            fold_test = {sym: df.loc[df.index.isin(test_ts)] for sym, df in data.items()}
            fold_train = {k_: v for k_, v in fold_train.items() if not v.empty}
            fold_test = {k_: v for k_, v in fold_test.items() if not v.empty}

            if not fold_train or not fold_test:
                continue

            score = self._run_backtest_metric(params, fold_test)
            if score is not None:
                scores.append(score)

        if not scores:
            return None, None

        mean = sum(scores) / len(scores)
        if len(scores) > 1:
            import math
            variance = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
            std = math.sqrt(variance)
        else:
            std = 0.0

        return mean, std

    def _suggest_params(
        self,
        trial: Any,  # optuna.Trial
        param_specs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Map param_specs to Optuna suggest_* calls."""
        params: Dict[str, Any] = {}
        for spec in param_specs:
            name = spec["name"]
            ptype = spec["type"]
            if ptype == "int":
                params[name] = trial.suggest_int(
                    name,
                    spec["low"],
                    spec["high"],
                    step=spec.get("step", 1),
                    log=spec.get("log", False),
                )
            elif ptype == "float":
                params[name] = trial.suggest_float(
                    name,
                    spec["low"],
                    spec["high"],
                    step=spec.get("step"),
                    log=spec.get("log", False),
                )
            elif ptype == "categorical":
                params[name] = trial.suggest_categorical(name, spec["choices"])
            else:
                raise ValueError(f"Unknown param type '{ptype}' for '{name}'")
        return params

    def _compute_param_stability(
        self,
        all_params: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute stability stats for each parameter across walk-forward windows."""
        if not all_params:
            return {}

        keys = list(all_params[0].keys())
        stability: Dict[str, Any] = {}

        for key in keys:
            vals = [p[key] for p in all_params if key in p]
            numeric_vals = [v for v in vals if isinstance(v, (int, float))]

            if numeric_vals:
                mean = sum(numeric_vals) / len(numeric_vals)
                if len(numeric_vals) > 1:
                    import math
                    var = sum((v - mean) ** 2 for v in numeric_vals) / (len(numeric_vals) - 1)
                    std = math.sqrt(var)
                else:
                    std = 0.0
                stability[key] = {
                    "mean": mean,
                    "std": std,
                    "min": min(numeric_vals),
                    "max": max(numeric_vals),
                    "values": numeric_vals,
                }
            else:
                # Categorical: find mode
                from collections import Counter
                counts = Counter(vals)
                mode = counts.most_common(1)[0][0] if counts else None
                stability[key] = {
                    "mode": mode,
                    "unique_values": list(counts.keys()),
                    "counts": dict(counts),
                }

        return stability
