from pydantic import BaseModel
from typing import Optional


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str  # "ma_cross" | "rsi" | "volume" | "custom"
    parameters: dict = {}


class StrategyOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    type: str
    parameters: dict
