"""PRISM Phase 3 — Strategy Comparison & Advanced Risk Analysis API.

Endpoints:
  POST /comparison/compare            — compare multiple backtest results
  GET  /comparison/{task_id}/stress   — stress test a single backtest
  POST /comparison/{task_id}/monte-carlo — Monte Carlo simulation
  POST /comparison/portfolio-risk     — portfolio-level risk for multiple strategies
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.analytics import compute_analytics, _equity_to_returns
from app.schemas.comparison import (
    ComparisonRequest,
    ComparisonResponse,
    CorrelationAnalysisResult,
    CorrelationPair,
    MarginalRiskContribution,
    MonteCarloRequest,
    MonteCarloResponse,
    PortfolioRiskResponse,
    StrategyComparisonEntry,
    StressScenarioResult,
    StressTestResponse,
)

# Allow importing risk module from project root
_root = Path(__file__).resolve().parents[5]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from risk.advanced_risk import (  # noqa: E402
    CorrelationAnalyzer,
    MonteCarloEngine,
    PortfolioRiskCalculator,
    StressTester,
)

router = APIRouter()

_RUNNING_STATES = {"PENDING", "STARTED", "PROGRESS"}


def _get_result(task_id: str) -> dict[str, Any]:
    """Fetch a completed Celery task result or raise an HTTP error."""
    from app.tasks.backtest_tasks import celery_app

    result = celery_app.AsyncResult(task_id)
    if result.state in _RUNNING_STATES:
        raise HTTPException(status_code=202, detail=f"Backtest still running: {result.state}")
    if result.state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.info))
    data = result.result
    if not data or "equity_curve" not in data:
        raise HTTPException(
            status_code=404,
            detail=f"No analytics data for task {task_id}. Ensure the backtest completed.",
        )
    return data


def _get_returns(task_id: str) -> tuple[list[float], dict[str, Any]]:
    """Return (returns_list, raw_result_data) for a task."""
    data = _get_result(task_id)
    returns = _equity_to_returns(data.get("equity_curve", []))
    return returns, data


# ---------------------------------------------------------------------------
# POST /comparison/compare
# ---------------------------------------------------------------------------

@router.post("/compare", response_model=ComparisonResponse)
async def compare_strategies(req: ComparisonRequest):
    """Compare multiple backtest results side-by-side with correlation analysis."""
    if len(req.task_ids) < 2:
        raise HTTPException(status_code=422, detail="At least 2 task_ids required.")

    entries: list[StrategyComparisonEntry] = []
    returns_by_id: dict[str, list[float]] = {}

    for tid in req.task_ids:
        returns, data = _get_returns(tid)
        analytics = compute_analytics(
            equity_curve=data.get("equity_curve", []),
            trades=data.get("trades", []),
        )
        perf = analytics["performance"]
        risk = analytics["risk"]

        entries.append(
            StrategyComparisonEntry(
                task_id=tid,
                strategy_name=data.get("strategy_name"),
                symbol=data.get("symbol"),
                total_return=perf["total_return"],
                annualised_return=perf["annualised_return"],
                sharpe_ratio=perf["sharpe_ratio"],
                sortino_ratio=perf["sortino_ratio"],
                max_drawdown=perf["max_drawdown"],
                calmar_ratio=perf["calmar_ratio"],
                win_rate=perf["win_rate"],
                profit_factor=perf["profit_factor"],
                annualised_volatility=perf["annualised_volatility"],
                total_trades=data.get("total_trades", 0),
                var_95=risk["var_95"],
                cvar_95=risk["cvar_95"],
            )
        )
        name = data.get("strategy_name") or tid[:8]
        returns_by_id[name] = returns

    best_sharpe = max(entries, key=lambda e: e.sharpe_ratio).task_id
    best_return = max(entries, key=lambda e: e.total_return).task_id
    lowest_dd = min(entries, key=lambda e: e.max_drawdown).task_id

    corr_result = CorrelationAnalyzer.compute(returns_by_id)
    correlation = CorrelationAnalysisResult(
        strategy_names=corr_result.strategy_names,
        correlation_matrix=corr_result.correlation_matrix,
        pairwise=[
            CorrelationPair(**p) for p in corr_result.pairwise
        ],
    )

    return ComparisonResponse(
        strategies=entries,
        best_sharpe=best_sharpe,
        best_return=best_return,
        lowest_drawdown=lowest_dd,
        correlation=correlation,
    )


# ---------------------------------------------------------------------------
# GET /comparison/{task_id}/stress
# ---------------------------------------------------------------------------

@router.get("/{task_id}/stress", response_model=StressTestResponse)
async def stress_test(task_id: str):
    """Run all named crisis scenarios against a completed backtest."""
    returns, data = _get_returns(task_id)

    if len(returns) < 5:
        raise HTTPException(
            status_code=422,
            detail="Insufficient return history for stress testing (need ≥5 periods).",
        )

    tester = StressTester(returns)
    results = tester.run_all()

    scenarios = [
        StressScenarioResult(
            scenario_name=r.scenario_name,
            peak_drawdown=round(r.peak_drawdown, 6),
            final_equity_ratio=round(r.final_equity_ratio, 6),
            recovery_periods=r.recovery_periods,
            metrics=r.metrics,
        )
        for r in results
    ]

    return StressTestResponse(
        task_id=task_id,
        strategy_name=data.get("strategy_name"),
        scenarios=scenarios,
    )


# ---------------------------------------------------------------------------
# POST /comparison/{task_id}/monte-carlo
# ---------------------------------------------------------------------------

@router.post("/{task_id}/monte-carlo", response_model=MonteCarloResponse)
async def monte_carlo(task_id: str, req: MonteCarloRequest):
    """Run a block-bootstrap Monte Carlo simulation for a completed backtest."""
    returns, data = _get_returns(task_id)

    if len(returns) < 10:
        raise HTTPException(
            status_code=422,
            detail="Insufficient return history for Monte Carlo (need ≥10 periods).",
        )

    engine = MonteCarloEngine(returns)
    result = engine.run(
        n_simulations=req.n_simulations,
        n_periods=req.n_periods,
    )

    return MonteCarloResponse(
        task_id=task_id,
        strategy_name=data.get("strategy_name"),
        n_simulations=result.n_simulations,
        n_periods=result.n_periods,
        percentiles=result.percentiles,
        final_equity_distribution=result.final_equity_distribution,
        prob_positive=result.prob_positive,
        prob_max_dd_exceeded=result.prob_max_dd_exceeded,
    )


# ---------------------------------------------------------------------------
# POST /comparison/portfolio-risk
# ---------------------------------------------------------------------------

@router.post("/portfolio-risk", response_model=PortfolioRiskResponse)
async def portfolio_risk(req: ComparisonRequest):
    """Compute portfolio-level risk for a multi-strategy allocation."""
    if len(req.task_ids) < 2:
        raise HTTPException(status_code=422, detail="At least 2 task_ids required.")

    strategies: dict[str, list[float]] = {}
    for tid in req.task_ids:
        returns, data = _get_returns(tid)
        name = data.get("strategy_name") or tid[:8]
        strategies[name] = returns

    calc = PortfolioRiskCalculator(
        strategies=strategies,
        weights=req.weights,
    )
    result = calc.compute()

    return PortfolioRiskResponse(
        n_strategies=result.n_strategies,
        task_ids=req.task_ids,
        weights=[round(w, 4) for w in result.weights],
        diversification_ratio=result.diversification_ratio,
        metrics=result.metrics,
        marginal_risk_contributions=[
            MarginalRiskContribution(**c) for c in result.marginal_risk_contributions
        ],
    )
