"""Data quality validation — gap detection, outlier filtering, consistency checks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from loguru import logger

from data.db import async_conn

INTERVAL_MINUTES: dict[str, int] = {
    "1": 1, "3": 3, "5": 5, "15": 15,
    "60": 60, "240": 240, "D": 1440, "W": 10080,
}


class IssueType(StrEnum):
    MISSING = "missing"
    GAP = "gap"
    OUTLIER = "outlier"
    STALE = "stale"
    NEGATIVE = "negative"
    OHLC_INVALID = "ohlc_invalid"


@dataclass
class QualityIssue:
    market: str
    interval: str | None
    issue_type: IssueType
    detail: dict[str, Any] = field(default_factory=dict)


# ─── OHLCV Checks ─────────────────────────────────────────────────────────────

def check_ohlc_validity(row: dict) -> list[QualityIssue]:
    issues = []
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]
    if h < max(o, c) or l > min(o, c):
        issues.append(QualityIssue(
            market=row["market"], interval=row["interval"],
            issue_type=IssueType.OHLC_INVALID,
            detail={"time": str(row["time"]), "open": str(o), "high": str(h),
                    "low": str(l), "close": str(c)},
        ))
    if any(v <= 0 for v in [o, h, l, c, row["volume"]]):
        issues.append(QualityIssue(
            market=row["market"], interval=row["interval"],
            issue_type=IssueType.NEGATIVE,
            detail={"time": str(row["time"])},
        ))
    return issues


def detect_price_outlier(price: Decimal, prev_price: Decimal, threshold: float = 0.20) -> bool:
    """Flag if price moved more than `threshold` (20%) from previous close."""
    if prev_price == 0:
        return False
    change = abs(float(price - prev_price) / float(prev_price))
    return change > threshold


# ─── Gap Detection ────────────────────────────────────────────────────────────

async def detect_gaps(
    market: str, interval: str, from_time: datetime, to_time: datetime
) -> list[QualityIssue]:
    """Find missing candles in [from_time, to_time] for a market/interval."""
    minutes = INTERVAL_MINUTES.get(interval)
    if minutes is None:
        return []

    async with async_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT time FROM candles
            WHERE market = $1 AND interval = $2
              AND time BETWEEN $3 AND $4
            ORDER BY time ASC
            """,
            market, interval, from_time, to_time,
        )

    if not rows:
        return [QualityIssue(
            market=market, interval=interval,
            issue_type=IssueType.MISSING,
            detail={"from": str(from_time), "to": str(to_time), "expected": "all"},
        )]

    issues = []
    expected_delta = timedelta(minutes=minutes)
    prev_time = rows[0]["time"]

    for row in rows[1:]:
        actual_delta = row["time"] - prev_time
        if actual_delta > expected_delta * 1.5:
            issues.append(QualityIssue(
                market=market, interval=interval,
                issue_type=IssueType.GAP,
                detail={
                    "gap_start": str(prev_time),
                    "gap_end": str(row["time"]),
                    "expected_minutes": minutes,
                    "actual_minutes": actual_delta.total_seconds() / 60,
                },
            ))
        prev_time = row["time"]

    return issues


async def check_staleness(market: str, max_age_seconds: int = 120) -> QualityIssue | None:
    """Return a staleness issue if the latest 1m candle is too old."""
    async with async_conn() as conn:
        row = await conn.fetchrow(
            "SELECT MAX(time) AS latest FROM candles WHERE market = $1 AND interval = '1'",
            market,
        )
    if not row or not row["latest"]:
        return QualityIssue(market=market, interval="1", issue_type=IssueType.STALE,
                            detail={"reason": "no data"})

    age = (datetime.now(tz=timezone.utc) - row["latest"]).total_seconds()
    if age > max_age_seconds:
        return QualityIssue(market=market, interval="1", issue_type=IssueType.STALE,
                            detail={"age_seconds": age, "latest": str(row["latest"])})
    return None


# ─── Persist & Report ─────────────────────────────────────────────────────────

async def log_issues(issues: list[QualityIssue]) -> None:
    if not issues:
        return
    rows = [
        (i.market, i.interval, str(i.issue_type), json.dumps(i.detail))
        for i in issues
    ]
    async with async_conn() as conn:
        await conn.executemany(
            """
            INSERT INTO data_quality_log (market, interval, issue_type, detail)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            rows,
        )
    logger.warning(f"Logged {len(issues)} data quality issue(s)")


async def run_quality_check(
    markets: list[str],
    interval: str = "1",
    lookback_hours: int = 1,
) -> list[QualityIssue]:
    now = datetime.now(tz=timezone.utc)
    from_time = now - timedelta(hours=lookback_hours)
    all_issues: list[QualityIssue] = []

    for market in markets:
        gap_issues = await detect_gaps(market, interval, from_time, now)
        all_issues.extend(gap_issues)

        stale = await check_staleness(market)
        if stale:
            all_issues.append(stale)

    if all_issues:
        await log_issues(all_issues)

    return all_issues
