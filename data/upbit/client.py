"""Upbit REST API client with rate-limit handling and retry logic."""
import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp
import jwt
import uuid
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from .models import Candle, Orderbook, Trade, Ticker, Market

UPBIT_BASE = "https://api.upbit.com/v1"

# Upbit rate limits: 10 req/s public, 30 req/s authenticated
_PUBLIC_RATE_LIMIT = 9    # conservative
_AUTH_RATE_LIMIT = 28


class RateLimiter:
    def __init__(self, rate: int):
        self._rate = rate
        self._tokens = rate
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


_public_limiter = RateLimiter(_PUBLIC_RATE_LIMIT)
_auth_limiter = RateLimiter(_AUTH_RATE_LIMIT)


class UpbitClient:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self):
        if self._owns_session:
            self._session = aiohttp.ClientSession(
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self

    async def __aexit__(self, *_):
        if self._owns_session and self._session:
            await self._session.close()

    def _auth_header(self, query: dict | None = None) -> dict:
        payload = {
            "access_key": settings.upbit_access_key,
            "nonce": str(uuid.uuid4()),
        }
        if query:
            import hashlib
            query_string = urlencode(query).encode()
            m = hashlib.sha512()
            m.update(query_string)
            payload["query_hash"] = m.hexdigest()
            payload["query_hash_alg"] = "SHA512"

        token = jwt.encode(payload, settings.upbit_secret_key, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def _get(self, path: str, params: dict | None = None, auth: bool = False) -> Any:
        limiter = _auth_limiter if auth else _public_limiter
        await limiter.acquire()

        headers = self._auth_header(params) if auth else {}
        url = f"{UPBIT_BASE}{path}"

        async with self._session.get(url, params=params, headers=headers) as resp:
            if resp.status == 429:
                retry_after = float(resp.headers.get("Retry-After", "1"))
                logger.warning(f"Rate limited on {path}, sleeping {retry_after}s")
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=429)
            resp.raise_for_status()
            return await resp.json()

    # ─── Market Info ──────────────────────────────────────────────────────────

    async def get_markets(self, only_krw: bool = True) -> list[Market]:
        data = await self._get("/market/all", params={"isDetails": "false"})
        markets = [Market(**m) for m in data]
        if only_krw:
            markets = [m for m in markets if m.market.startswith("KRW-")]
        return markets

    # ─── Candles ──────────────────────────────────────────────────────────────

    async def get_minute_candles(
        self,
        market: str,
        unit: int = 1,
        count: int = 200,
        to: datetime | None = None,
    ) -> list[Candle]:
        params: dict = {"market": market, "count": min(count, 200)}
        if to:
            params["to"] = to.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await self._get(f"/candles/minutes/{unit}", params=params)
        return [Candle(**c) for c in data]

    async def get_day_candles(
        self,
        market: str,
        count: int = 200,
        to: datetime | None = None,
        converting_price_unit: str = "KRW",
    ) -> list[Candle]:
        params: dict = {
            "market": market,
            "count": min(count, 200),
            "convertingPriceUnit": converting_price_unit,
        }
        if to:
            params["to"] = to.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await self._get("/candles/days", params=params)
        return [Candle(**c) for c in data]

    async def get_week_candles(
        self,
        market: str,
        count: int = 200,
        to: datetime | None = None,
    ) -> list[Candle]:
        params: dict = {"market": market, "count": min(count, 200)}
        if to:
            params["to"] = to.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = await self._get("/candles/weeks", params=params)
        return [Candle(**c) for c in data]

    # ─── Order Book ───────────────────────────────────────────────────────────

    async def get_orderbook(self, markets: list[str]) -> list[Orderbook]:
        params = {"markets": ",".join(markets)}
        data = await self._get("/orderbook", params=params)
        return [Orderbook(**o) for o in data]

    # ─── Trades ───────────────────────────────────────────────────────────────

    async def get_trades(
        self,
        market: str,
        count: int = 100,
        cursor: str | None = None,
        days_ago: int | None = None,
        to: str | None = None,
    ) -> list[Trade]:
        params: dict = {"market": market, "count": min(count, 100)}
        if cursor:
            params["cursor"] = cursor
        if days_ago is not None:
            params["daysAgo"] = days_ago
        if to:
            params["to"] = to
        data = await self._get("/trades/ticks", params=params)
        return [Trade(**t) for t in data]

    # ─── Tickers ──────────────────────────────────────────────────────────────

    async def get_tickers(self, markets: list[str]) -> list[Ticker]:
        params = {"markets": ",".join(markets)}
        data = await self._get("/ticker", params=params)
        return [Ticker(**t) for t in data]
