"""Pydantic models for KIS (한국투자증권) Open Trading API responses."""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class KISToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int          # seconds until expiry (typically 86400 = 24h)
    access_token_token_expired: str  # expiry datetime string


class StockCandle(BaseModel):
    """OHLCV candle for a Korean stock (daily or minute)."""
    ticker: str
    market_div: Literal["J", "Q"]   # J=KOSPI, Q=KOSDAQ
    interval: str                    # "1","5","15","30","60","D"
    time: datetime                   # UTC
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_value: Decimal = Decimal(0)   # 거래대금 (KRW)


class StockInfo(BaseModel):
    """Basic stock metadata from the KIS API."""
    ticker: str          # 6-digit code, e.g. "005930"
    name: str            # 종목명
    market_div: Literal["J", "Q"]
    sector: str = ""
    listed_shares: int = 0


class DailyCandleRaw(BaseModel):
    """Raw daily candle from KIS output2 array."""
    stck_bsop_date: str   # YYYYMMDD
    stck_oprc: str        # 시가 (open)
    stck_hgpr: str        # 고가 (high)
    stck_lwpr: str        # 저가 (low)
    stck_clpr: str        # 종가 (close)
    acml_vol: str         # 누적거래량
    acml_tr_pbmn: str = "0"  # 누적거래대금

    @field_validator("stck_oprc", "stck_hgpr", "stck_lwpr", "stck_clpr",
                     "acml_vol", "acml_tr_pbmn", mode="before")
    @classmethod
    def strip_empty(cls, v):
        return v or "0"

    def to_candle(self, ticker: str, market_div: Literal["J", "Q"]) -> StockCandle:
        d = date(
            int(self.stck_bsop_date[:4]),
            int(self.stck_bsop_date[4:6]),
            int(self.stck_bsop_date[6:8]),
        )
        # Daily candle: timestamp at 15:30 KST (06:30 UTC)
        from datetime import timezone, timedelta
        kst = timezone(timedelta(hours=9))
        dt = datetime(d.year, d.month, d.day, 15, 30, tzinfo=kst).astimezone(timezone.utc)
        return StockCandle(
            ticker=ticker,
            market_div=market_div,
            interval="D",
            time=dt.replace(tzinfo=None),
            open=Decimal(self.stck_oprc),
            high=Decimal(self.stck_hgpr),
            low=Decimal(self.stck_lwpr),
            close=Decimal(self.stck_clpr),
            volume=int(self.acml_vol),
            trade_value=Decimal(self.acml_tr_pbmn),
        )


class MinuteCandleRaw(BaseModel):
    """Raw minute candle from KIS output2 array."""
    stck_cntg_hour: str   # HHmmss
    stck_oprc: str        # 시가
    stck_hgpr: str        # 고가
    stck_lwpr: str        # 저가
    stck_prpr: str        # 현재가 (close for this candle)
    cntg_vol: str         # 체결거래량 (volume for this candle)
    acml_tr_pbmn: str = "0"  # 누적거래대금

    @field_validator("stck_oprc", "stck_hgpr", "stck_lwpr", "stck_prpr",
                     "cntg_vol", "acml_tr_pbmn", mode="before")
    @classmethod
    def strip_empty(cls, v):
        return v or "0"

    def to_candle(
        self,
        ticker: str,
        market_div: Literal["J", "Q"],
        interval: str,
        trade_date: date,
    ) -> StockCandle:
        from datetime import timezone, timedelta
        hh = int(self.stck_cntg_hour[:2])
        mm = int(self.stck_cntg_hour[2:4])
        ss = int(self.stck_cntg_hour[4:6])
        kst = timezone(timedelta(hours=9))
        dt = datetime(trade_date.year, trade_date.month, trade_date.day,
                      hh, mm, ss, tzinfo=kst).astimezone(timezone.utc)
        return StockCandle(
            ticker=ticker,
            market_div=market_div,
            interval=interval,
            time=dt.replace(tzinfo=None),
            open=Decimal(self.stck_oprc),
            high=Decimal(self.stck_hgpr),
            low=Decimal(self.stck_lwpr),
            close=Decimal(self.stck_prpr),
            volume=int(self.cntg_vol),
            trade_value=Decimal(self.acml_tr_pbmn),
        )


class CurrentPriceRaw(BaseModel):
    """현재가 조회 output1 — used for staleness checks and live monitoring."""
    stck_prpr: str        # 현재가
    stck_oprc: str        # 시가
    stck_hgpr: str        # 고가
    stck_lwpr: str        # 저가
    acml_vol: str         # 누적거래량
    acml_tr_pbmn: str = "0"
    prdy_vrss: str = "0"  # 전일대비
    prdy_ctrt: str = "0"  # 전일대비율

    @property
    def current_price(self) -> Decimal:
        return Decimal(self.stck_prpr or "0")
