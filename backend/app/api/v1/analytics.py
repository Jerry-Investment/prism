from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.core.analytics import compute_analytics
from app.core.report import generate_html_report
from app.schemas.analytics import AnalyticsResponse

router = APIRouter()

_RUNNING_STATES = {"PENDING", "STARTED", "PROGRESS"}


def _get_result(task_id: str):
    """Fetch Celery task result, raising appropriate HTTP errors."""
    from app.tasks.backtest_tasks import celery_app

    result = celery_app.AsyncResult(task_id)
    if result.state in _RUNNING_STATES:
        raise HTTPException(
            status_code=202,
            detail=f"Backtest still running: {result.state}",
        )
    if result.state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.info))
    data = result.result
    if not data or "equity_curve" not in data:
        raise HTTPException(
            status_code=404,
            detail="No analytics data for this task. Ensure the backtest completed successfully.",
        )
    return data


@router.get("/{task_id}", response_model=AnalyticsResponse)
async def get_analytics(task_id: str):
    """Return full performance and risk analytics for a completed backtest."""
    data = _get_result(task_id)
    analytics = compute_analytics(
        equity_curve=data["equity_curve"],
        trades=data.get("trades", []),
    )
    return AnalyticsResponse(
        task_id=task_id,
        strategy_name=data.get("strategy_name"),
        symbol=data.get("symbol"),
        total_trades=data.get("total_trades", 0),
        initial_capital=data.get("initial_capital", 0.0),
        final_equity=data.get("final_equity", 0.0),
        equity_curve=data.get("equity_curve", []),
        performance=analytics["performance"],
        risk=analytics["risk"],
        monthly_returns=analytics["monthly_returns"],
        yearly_returns=analytics["yearly_returns"],
    )


@router.get("/{task_id}/report", response_class=HTMLResponse)
async def get_report(task_id: str):
    """Return an HTML performance report for a completed backtest."""
    data = _get_result(task_id)
    analytics = compute_analytics(
        equity_curve=data.get("equity_curve", []),
        trades=data.get("trades", []),
    )
    html = generate_html_report(
        task_id=task_id,
        strategy_name=data.get("strategy_name", "Unknown"),
        symbol=data.get("symbol", "Unknown"),
        initial_capital=data.get("initial_capital", 0.0),
        final_equity=data.get("final_equity", 0.0),
        total_trades=data.get("total_trades", 0),
        analytics=analytics,
        equity_curve=data.get("equity_curve", []),
    )
    return HTMLResponse(content=html)
