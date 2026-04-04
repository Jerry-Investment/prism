from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    strategy_id: str
    symbols: list[str] = Field(default=["KRW-BTC"], min_length=1)
    interval: str = Field(default="1d")
    initial_capital: float = Field(default=10_000_000, ge=1000)
    strategy_params: Optional[dict] = None


class PositionOut(BaseModel):
    id: int
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    symbol: str
    action: str
    quantity: float
    price: float
    commission: float
    status: str
    reject_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: int
    alert_type: str
    message: str
    symbol: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: int
    strategy_id: str
    symbols: str
    interval: str
    initial_capital: float
    current_cash: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    positions: list[PositionOut] = []

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    id: int
    strategy_id: str
    symbols: str
    status: str
    initial_capital: float
    current_cash: float
    equity: float
    total_return_pct: float
    created_at: datetime

    model_config = {"from_attributes": True}
