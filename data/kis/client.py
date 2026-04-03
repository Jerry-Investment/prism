"""KIS (한국투자증권) Open Trading API client.

Authentication:
- POST /oauth2/tokenP  →  access_token (valid 24 h)
- All requests: Authorization: Bearer {token}
                appkey: {app_key}
                appsecret: {app_secret}

Rate limits: ~20 req/s per TR_ID; we stay at 15 req/s to be safe.

KIS real-account base URL: https://openapi.koreainvestment.com:9443
KIS paper-trading base URL: https://openapivts.koreainvestment.com:29443
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timezone, timedelta
from typing import Any, Literal

import aiohttp
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from .models import (
    DailyCandleRaw,
    MinuteCandleRaw,
    CurrentPriceRaw,
    KISToken,
    StockCandle,
    StockInfo,
)

KST = timezone(timedelta(hours=9))
MAX_DAILY_PER_CALL = 100    # KIS returns max 100 daily candles per request
MAX_MINUTE_PER_CALL = 30    # KIS returns max 30 minute candles per request


class RateLimiter:
    def __init__(self, rate: int):
        self._rate = rate
        self._tokens = float(rate)
        self._last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last_refill = now
            if self._tokens >= 1:
                self._tokens -= 1
                return
            await asyncio.sleep(1 / self._rate)


_limiter = RateLimiter(15)   # conservative — well below 20 req/s limit


class KISClient:
    """Async KIS REST API client with automatic token refresh."""

    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._owns_session = session is None
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def __aenter__(self) -> "KISClient":
        if self._owns_session:
            self._session = aiohttp.ClientSession(
                headers={"content-type": "application/json; charset=utf-8"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
        await self._ensure_token()
        return self

    async def __aexit__(self, *_) -> None:
        if self._owns_session and self._session:
            await self._session.close()

    # ─── Auth ─────────────────────────────────────────────────────────────────

    async def _ensure_token(self) -> None:
        """Refresh the access token if missing or within 60s of expiry."""
        if (
            self._token
            and self._token_expires_at
            and datetime.now(tz=timezone.utc) < self._token_expires_at - timedelta(seconds=60)
        ):
            return

        await self._refresh_token()

    async def _refresh_token(self) -> None:
        url = f"{settings.kis_base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
        }
        async with self._session.post(url, json=body) as resp:
            resp.raise_for_status()
            data = await resp.json()

        token = KISToken(**data)
        self._token = token.access_token
        self._token_expires_at = datetime.now(tz=timezone.utc) + timedelta(
            seconds=token.expires_in
        )
        logger.info(
            f"KIS token refreshed — expires at {self._token_expires_at.isoformat()}"
        )

    def _headers(self, tr_id: str) -> dict:
        return {
            "authorization": f"Bearer {self._token}",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    # ─── HTTP helpers ─────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def _get(self, path: str, tr_id: str, params: dict) -> Any:
        await self._ensure_token()
        await _limiter.acquire()

        url = f"{settings.kis_base_url}{path}"
        async with self._session.get(url, params=params, headers=self._headers(tr_id)) as resp:
            if resp.status == 429:
                retry_after = float(resp.headers.get("Retry-After", "1"))
                logger.warning(f"KIS rate-limited on {path}, sleeping {retry_after}s")
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=429)
            resp.raise_for_status()
            return await resp.json()

    # ─── Current price (현재가) ───────────────────────────────────────────────

    async def get_current_price(
        self, ticker: str, market_div: Literal["J", "Q"] = "J"
    ) -> CurrentPriceRaw:
        """현재가 조회 — FHKST01010100."""
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": ticker,
            },
        )
        return CurrentPriceRaw(**data["output"])

    # ─── Daily candles (일봉) ─────────────────────────────────────────────────

    async def get_daily_candles(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        market_div: Literal["J", "Q"] = "J",
        adjusted: bool = True,
    ) -> list[StockCandle]:
        """일봉 차트 조회 — FHKST03010100.

        KIS returns up to 100 candles per call in descending date order.
        `adjusted=True` fetches 수정주가 (split/dividend adjusted).
        """
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            tr_id="FHKST03010100",
            params={
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": ticker,
                "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0" if adjusted else "1",
            },
        )
        raw_list: list[dict] = data.get("output2", [])
        candles = []
        for row in raw_list:
            try:
                raw = DailyCandleRaw(**row)
                if not raw.stck_bsop_date or raw.stck_bsop_date == "0":
                    continue
                candles.append(raw.to_candle(ticker, market_div))
            except Exception as e:
                logger.warning(f"Skipping malformed daily row for {ticker}: {e}")
        return candles

    # ─── Minute candles (분봉) ────────────────────────────────────────────────

    async def get_minute_candles(
        self,
        ticker: str,
        interval_minutes: int = 1,
        market_div: Literal["J", "Q"] = "J",
        to_time: str | None = None,
    ) -> list[StockCandle]:
        """분봉 차트 조회 — FHKST03010200.

        Returns up to 30 candles ending at `to_time` (HHmmss, defaults to now).
        `interval_minutes` must be one of 1, 3, 5, 10, 15, 30, 60.
        """
        trade_date = datetime.now(tz=KST).date()
        if to_time is None:
            to_time = datetime.now(tz=KST).strftime("%H%M%S")

        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            tr_id="FHKST03010200",
            params={
                "FID_ETC_CLS_CODE": "",
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_ISCD": ticker,
                "FID_INPUT_HOUR_1": to_time,
                "FID_PW_DATA_INCU_YN": "N",
            },
        )
        raw_list: list[dict] = data.get("output2", [])
        interval_str = str(interval_minutes)
        candles = []
        for row in raw_list:
            try:
                raw = MinuteCandleRaw(**row)
                if not raw.stck_cntg_hour or raw.stck_cntg_hour == "000000":
                    continue
                candles.append(raw.to_candle(ticker, market_div, interval_str, trade_date))
            except Exception as e:
                logger.warning(f"Skipping malformed minute row for {ticker}: {e}")
        return candles

    # ─── Stock list (종목 목록) ───────────────────────────────────────────────

    async def get_kospi200_tickers(self) -> list[StockInfo]:
        """KOSPI 200 구성종목 조회 — FHPUP02100000.

        Returns the current KOSPI 200 index constituents.
        """
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-index-components",
            tr_id="FHPUP02100000",
            params={
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": "0028",   # 0028 = KOSPI 200 index code
            },
        )
        raw_list: list[dict] = data.get("output2", [])
        stocks = []
        for row in raw_list:
            ticker = row.get("mksc_shrn_iscd", "").strip()
            name = row.get("hts_kor_isnm", "").strip()
            if ticker and name:
                stocks.append(StockInfo(
                    ticker=ticker,
                    name=name,
                    market_div="J",
                ))
        return stocks
