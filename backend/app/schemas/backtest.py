from pydantic import BaseModel, Field
from typing import Optional, Any


class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str = Field(default="KRW-BTC")
    interval: str = Field(default="1d")
    start: str = Field(description="ISO date string, e.g. 2024-01-01")
    end: str = Field(description="ISO date string, e.g. 2024-12-31")
    initial_capital: float = Field(default=10_000_000, ge=0)
    params: dict = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    task_id: str
    status: str


class BacktestStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
