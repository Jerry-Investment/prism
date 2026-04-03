from fastapi import APIRouter, HTTPException
from app.schemas.backtest import BacktestRequest, BacktestResponse, BacktestStatus
from app.tasks.backtest_tasks import run_backtest_task

router = APIRouter()


@router.post("/", response_model=BacktestResponse, status_code=202)
async def create_backtest(request: BacktestRequest):
    """Submit a new backtest job."""
    task = run_backtest_task.delay(request.model_dump())
    return BacktestResponse(task_id=task.id, status="queued")


@router.get("/{task_id}", response_model=BacktestStatus)
async def get_backtest_status(task_id: str):
    """Get the status and result of a backtest task."""
    from app.tasks.backtest_tasks import celery_app
    result = celery_app.AsyncResult(task_id)
    if result.state == "PENDING":
        return BacktestStatus(task_id=task_id, status="pending")
    elif result.state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.info))
    return BacktestStatus(task_id=task_id, status=result.state.lower(), result=result.result)
