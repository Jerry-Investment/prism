"""Pydantic models for Upbit API responses."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class Candle(BaseModel):
    market: str
    candle_date_time_utc: datetime
    candle_date_time_kst: datetime
    opening_price: Decimal
    high_price: Decimal
    low_price: Decimal
    trade_price: Decimal
    timestamp: int
    candle_acc_trade_price: Decimal
    candle_acc_trade_volume: Decimal
    unit: int | None = None           # minutes candle: 1, 3, 5, 15, 60, 240
    prev_closing_price: Decimal | None = None
    change_price: Decimal | None = None
    change_rate: Decimal | None = None


class OrderbookUnit(BaseModel):
    ask_price: Decimal
    bid_price: Decimal
    ask_size: Decimal
    bid_size: Decimal


class Orderbook(BaseModel):
    market: str
    timestamp: int
    total_ask_size: Decimal
    total_bid_size: Decimal
    orderbook_units: list[OrderbookUnit]


class Trade(BaseModel):
    market: str
    trade_date_utc: str
    trade_time_utc: str
    timestamp: int
    trade_price: Decimal
    trade_volume: Decimal
    prev_closing_price: Decimal
    change_price: Decimal
    ask_bid: Literal["ASK", "BID"]
    sequential_id: int

    @property
    def trade_datetime(self) -> datetime:
        return datetime.strptime(
            f"{self.trade_date_utc} {self.trade_time_utc}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=None)


class Ticker(BaseModel):
    market: str
    trade_date: str
    trade_time: str
    trade_date_kst: str
    trade_time_kst: str
    trade_timestamp: int
    opening_price: Decimal
    high_price: Decimal
    low_price: Decimal
    trade_price: Decimal
    prev_closing_price: Decimal
    change: str
    change_price: Decimal
    change_rate: Decimal
    signed_change_price: Decimal
    signed_change_rate: Decimal
    trade_volume: Decimal
    acc_trade_price: Decimal
    acc_trade_price_24h: Decimal
    acc_trade_volume: Decimal
    acc_trade_volume_24h: Decimal
    highest_52_week_price: Decimal
    highest_52_week_date: str
    lowest_52_week_price: Decimal
    lowest_52_week_date: str
    timestamp: int


class Market(BaseModel):
    market: str
    korean_name: str
    english_name: str
    market_event: dict | None = None
