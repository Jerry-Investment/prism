from fastapi import APIRouter
from app.schemas.strategy import StrategyCreate, StrategyOut

router = APIRouter()

# In-memory store for Phase 1 — replace with DB in Phase 2
_strategies: dict[str, dict] = {}


@router.get("/", response_model=list[StrategyOut])
async def list_strategies():
    return list(_strategies.values())


@router.post("/", response_model=StrategyOut, status_code=201)
async def create_strategy(payload: StrategyCreate):
    import uuid
    sid = str(uuid.uuid4())
    strategy = {"id": sid, **payload.model_dump()}
    _strategies[sid] = strategy
    return strategy


@router.get("/{strategy_id}", response_model=StrategyOut)
async def get_strategy(strategy_id: str):
    from fastapi import HTTPException
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategies[strategy_id]


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: str):
    from fastapi import HTTPException
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    del _strategies[strategy_id]
