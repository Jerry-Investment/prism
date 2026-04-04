"""
Paper Trading API — Phase 3

Endpoints:
  POST   /paper-trading/sessions           Create a new session
  GET    /paper-trading/sessions           List user's sessions
  GET    /paper-trading/sessions/{id}      Get session + positions
  DELETE /paper-trading/sessions/{id}      Stop (deactivate) a session
  GET    /paper-trading/sessions/{id}/orders    Order history
  GET    /paper-trading/sessions/{id}/alerts    Alert history
  POST   /paper-trading/sessions/{id}/tick      Manually trigger one evaluation cycle
  WS     /paper-trading/sessions/{id}/ws        Real-time updates
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.paper_trading_engine import compute_equity, evaluate_and_execute, update_prices
from app.db.session import get_db
from app.models.paper_trading import (
    PaperTradingAlert,
    PaperTradingOrder,
    PaperTradingPosition,
    PaperTradingSession,
    SessionStatus,
)
from app.models.user import User
from app.schemas.paper_trading import (
    AlertOut,
    OrderOut,
    SessionCreate,
    SessionOut,
    SessionSummary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory registry of active WebSocket connections per session
# session_id → set of WebSocket objects
_ws_connections: dict[int, set[WebSocket]] = {}


async def _broadcast(session_id: int, payload: dict) -> None:
    conns = _ws_connections.get(session_id, set())
    dead = set()
    for ws in list(conns):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)
    conns -= dead


# ── REST endpoints ────────────────────────────────────────────────────────────


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new paper trading session."""
    session = PaperTradingSession(
        user_id=current_user.id,
        strategy_id=body.strategy_id,
        symbols=",".join(body.symbols),
        interval=body.interval,
        initial_capital=body.initial_capital,
        current_cash=body.initial_capital,
        strategy_params=json.dumps(body.strategy_params) if body.strategy_params else None,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all paper trading sessions for the current user."""
    result = await db.execute(
        select(PaperTradingSession)
        .where(PaperTradingSession.user_id == current_user.id)
        .options(selectinload(PaperTradingSession.positions))
        .order_by(PaperTradingSession.created_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        pos_value = sum(p.market_value for p in s.positions if p.quantity > 0)
        equity = s.current_cash + pos_value
        total_return_pct = (equity / s.initial_capital - 1.0) * 100 if s.initial_capital else 0.0
        out.append(
            SessionSummary(
                id=s.id,
                strategy_id=s.strategy_id,
                symbols=s.symbols,
                status=s.status.value,
                initial_capital=s.initial_capital,
                current_cash=s.current_cash,
                equity=equity,
                total_return_pct=total_return_pct,
                created_at=s.created_at,
            )
        )
    return out


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = await _get_owned_session(db, session_id, current_user.id)
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def stop_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stop an active paper trading session."""
    session = await _get_owned_session(db, session_id, current_user.id)
    if session.status == SessionStatus.active:
        session.status = SessionStatus.stopped
        await db.commit()
    await _broadcast(session_id, {"type": "session_stopped", "session_id": session_id})


@router.get("/sessions/{session_id}/orders", response_model=list[OrderOut])
async def get_orders(
    session_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _get_owned_session(db, session_id, current_user.id)
    result = await db.execute(
        select(PaperTradingOrder)
        .where(PaperTradingOrder.session_id == session_id)
        .order_by(PaperTradingOrder.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/alerts", response_model=list[AlertOut])
async def get_alerts(
    session_id: int,
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _get_owned_session(db, session_id, current_user.id)
    q = select(PaperTradingAlert).where(PaperTradingAlert.session_id == session_id)
    if unread_only:
        q = q.where(PaperTradingAlert.is_read.is_(False))
    q = q.order_by(PaperTradingAlert.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/sessions/{session_id}/tick", status_code=200)
async def manual_tick(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Manually trigger one evaluation cycle: fetch latest prices, run strategy,
    execute signals, check risk. Broadcasts events over WebSocket.
    """
    session = await _get_owned_session(db, session_id, current_user.id)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=400, detail="Session is not active")

    events = await evaluate_and_execute(db, session)
    await db.commit()

    for event in events:
        await _broadcast(session_id, event)

    # Also broadcast updated positions
    await _broadcast_positions(db, session_id)

    return {"events_count": len(events), "events": events}


# ── WebSocket ─────────────────────────────────────────────────────────────────


@router.websocket("/sessions/{session_id}/ws")
async def paper_trading_ws(
    session_id: int,
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time paper trading updates.

    On connect: sends current portfolio snapshot.
    Accepts messages: {"action": "tick"} to trigger an evaluation cycle.
    Broadcasts: order, alert, portfolio_update, position_update events.
    """
    await websocket.accept()

    # Register connection
    if session_id not in _ws_connections:
        _ws_connections[session_id] = set()
    _ws_connections[session_id].add(websocket)

    try:
        # Send initial snapshot
        result = await db.execute(
            select(PaperTradingSession)
            .where(PaperTradingSession.id == session_id)
            .options(selectinload(PaperTradingSession.positions))
        )
        session = result.scalar_one_or_none()
        if session is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            return

        equity = await compute_equity(db, session)
        await websocket.send_json(
            {
                "type": "init",
                "session_id": session_id,
                "status": session.status.value,
                "equity": equity,
                "cash": session.current_cash,
                "initial_capital": session.initial_capital,
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "avg_cost": p.avg_cost,
                        "current_price": p.current_price,
                        "market_value": p.market_value,
                        "unrealized_pnl": p.unrealized_pnl,
                        "unrealized_pnl_pct": p.unrealized_pnl_pct,
                    }
                    for p in session.positions
                    if p.quantity > 0
                ],
            }
        )

        # Auto-tick loop: evaluate every 60 seconds while session is active
        async def auto_tick():
            while True:
                await asyncio.sleep(60)
                try:
                    # Re-fetch session inside fresh db context
                    res = await db.execute(
                        select(PaperTradingSession).where(
                            PaperTradingSession.id == session_id
                        )
                    )
                    s = res.scalar_one_or_none()
                    if s is None or s.status != SessionStatus.active:
                        break
                    events = await evaluate_and_execute(db, s)
                    await db.commit()
                    for ev in events:
                        await _broadcast(session_id, ev)
                    await _broadcast_positions(db, session_id)
                except Exception as exc:
                    logger.warning("Auto-tick error for session %d: %s", session_id, exc)
                    break

        tick_task = asyncio.create_task(auto_tick())

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if msg.get("action") == "tick":
                    res = await db.execute(
                        select(PaperTradingSession).where(
                            PaperTradingSession.id == session_id
                        )
                    )
                    s = res.scalar_one_or_none()
                    if s and s.status == SessionStatus.active:
                        events = await evaluate_and_execute(db, s)
                        await db.commit()
                        for ev in events:
                            await _broadcast(session_id, ev)
                        await _broadcast_positions(db, session_id)

                elif msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})

        finally:
            tick_task.cancel()

    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.get(session_id, set()).discard(websocket)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_owned_session(
    db: AsyncSession, session_id: int, user_id: int
) -> PaperTradingSession:
    result = await db.execute(
        select(PaperTradingSession)
        .where(
            PaperTradingSession.id == session_id,
            PaperTradingSession.user_id == user_id,
        )
        .options(selectinload(PaperTradingSession.positions))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _broadcast_positions(db: AsyncSession, session_id: int) -> None:
    result = await db.execute(
        select(PaperTradingPosition).where(
            PaperTradingPosition.session_id == session_id,
            PaperTradingPosition.quantity > 0,
        )
    )
    positions = result.scalars().all()
    await _broadcast(
        session_id,
        {
            "type": "position_update",
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": p.avg_cost,
                    "current_price": p.current_price,
                    "market_value": p.market_value,
                    "unrealized_pnl": p.unrealized_pnl,
                    "unrealized_pnl_pct": p.unrealized_pnl_pct,
                }
                for p in positions
            ],
        },
    )
