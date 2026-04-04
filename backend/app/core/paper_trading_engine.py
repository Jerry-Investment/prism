"""
Paper Trading Engine — Phase 3

Responsibilities:
- Fetch latest market prices from Upbit
- Load strategy by ID and evaluate signals on recent OHLCV data
- Execute virtual orders (buy/sell) against a session's cash and positions
- Track unrealized P&L and update positions
- Generate alerts for signals and risk breaches
"""

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_layer import fetch_ohlcv
from app.models.paper_trading import (
    AlertType,
    OrderAction,
    OrderStatus,
    PaperTradingAlert,
    PaperTradingOrder,
    PaperTradingPosition,
    PaperTradingSession,
)

logger = logging.getLogger(__name__)

# Commission rate matching Upbit taker fee
COMMISSION_RATE = 0.0005  # 0.05%

# Risk thresholds
DRAWDOWN_WARNING_PCT = 5.0    # alert at 5% drawdown from initial capital
DRAWDOWN_CRITICAL_PCT = 10.0  # alert at 10% drawdown


def _load_strategy(strategy_id: str, params: Optional[dict] = None):
    """Return an instantiated Strategy by ID. Falls back to a no-op hold strategy."""
    from app.core.strategy import Strategy, Signal
    import pandas as pd

    # Import concrete strategies registered in prism/strategy/
    try:
        import importlib
        mod = importlib.import_module(f"prism.strategy.{strategy_id}")
        cls = getattr(mod, strategy_id.replace("_", " ").title().replace(" ", ""))
        return cls(params or {})
    except (ImportError, AttributeError):
        pass

    # Built-in strategies mapped by id
    from prism.strategy.strategies import MACrossStrategy, RSIStrategy, VolumeStrategy

    built_in = {
        "ma_cross": MACrossStrategy,
        "rsi": RSIStrategy,
        "volume": VolumeStrategy,
    }
    if strategy_id in built_in:
        return built_in[strategy_id](params or {})

    # Unknown strategy — use hold-only no-op
    class _HoldStrategy(Strategy):
        name = "hold"

        def generate_signals(self, ohlcv: pd.DataFrame):
            return []

    logger.warning("Unknown strategy_id=%s — using hold strategy", strategy_id)
    return _HoldStrategy()


async def _get_or_create_position(
    db: AsyncSession, session_id: int, symbol: str
) -> PaperTradingPosition:
    result = await db.execute(
        select(PaperTradingPosition).where(
            PaperTradingPosition.session_id == session_id,
            PaperTradingPosition.symbol == symbol,
        )
    )
    pos = result.scalar_one_or_none()
    if pos is None:
        pos = PaperTradingPosition(session_id=session_id, symbol=symbol)
        db.add(pos)
    return pos


async def _add_alert(
    db: AsyncSession,
    session_id: int,
    alert_type: AlertType,
    message: str,
    symbol: Optional[str] = None,
) -> PaperTradingAlert:
    alert = PaperTradingAlert(
        session_id=session_id,
        alert_type=alert_type,
        message=message,
        symbol=symbol,
    )
    db.add(alert)
    return alert


async def update_prices(
    db: AsyncSession, session: PaperTradingSession
) -> dict[str, float]:
    """Fetch latest prices for all symbols in the session and update positions."""
    prices: dict[str, float] = {}
    for symbol in session.symbol_list:
        try:
            bars = await fetch_ohlcv(symbol, interval="1m", limit=1)
            if bars:
                price = bars[-1].close
                prices[symbol] = price
                pos = await _get_or_create_position(db, session.id, symbol)
                pos.current_price = price
        except Exception as exc:
            logger.warning("Failed to fetch price for %s: %s", symbol, exc)
    return prices


async def compute_equity(
    db: AsyncSession, session: PaperTradingSession
) -> float:
    """Return total equity = cash + sum of open position market values."""
    result = await db.execute(
        select(PaperTradingPosition).where(
            PaperTradingPosition.session_id == session.id,
            PaperTradingPosition.quantity > 0,
        )
    )
    positions = result.scalars().all()
    pos_value = sum(p.market_value for p in positions)
    return session.current_cash + pos_value


async def evaluate_and_execute(
    db: AsyncSession, session: PaperTradingSession
) -> list[dict]:
    """
    Run one evaluation cycle:
    1. Fetch latest OHLCV history for each symbol
    2. Ask strategy to generate signals
    3. Execute any buy/sell signals as paper orders
    4. Check risk and emit alerts
    Returns list of event dicts for WebSocket broadcast.
    """
    events: list[dict] = []

    strategy_params = json.loads(session.strategy_params) if session.strategy_params else {}
    strategy = _load_strategy(session.strategy_id, strategy_params)

    prices = await update_prices(db, session)

    for symbol in session.symbol_list:
        try:
            bars = await fetch_ohlcv(symbol, interval=session.interval, limit=100)
        except Exception as exc:
            logger.warning("OHLCV fetch failed for %s: %s", symbol, exc)
            continue

        if len(bars) < 2:
            continue

        import pandas as pd

        ohlcv_df = pd.DataFrame(
            [
                {
                    "timestamp": b.timestamp,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ]
        )

        try:
            signals = strategy.generate_signals(ohlcv_df)
        except Exception as exc:
            logger.warning("Strategy signal error for %s: %s", symbol, exc)
            continue

        current_price = prices.get(symbol, bars[-1].close)

        for signal in signals:
            if signal.symbol != symbol:
                continue
            if signal.action == "hold":
                continue

            order_event = await _execute_signal(
                db, session, signal, symbol, current_price
            )
            if order_event:
                events.append(order_event)

                # Emit signal alert
                alert = await _add_alert(
                    db,
                    session.id,
                    AlertType.signal,
                    f"{signal.action.upper()} signal for {symbol} @ {current_price:,.0f}",
                    symbol=symbol,
                )
                events.append(
                    {
                        "type": "alert",
                        "alert_type": "signal",
                        "message": alert.message,
                        "symbol": symbol,
                    }
                )

    # Risk check
    equity = await compute_equity(db, session)
    drawdown_pct = (1.0 - equity / session.initial_capital) * 100
    if drawdown_pct >= DRAWDOWN_CRITICAL_PCT:
        alert = await _add_alert(
            db,
            session.id,
            AlertType.risk,
            f"CRITICAL: drawdown {drawdown_pct:.1f}% exceeds {DRAWDOWN_CRITICAL_PCT}% threshold. "
            "Consider stopping the session.",
        )
        events.append({"type": "alert", "alert_type": "risk", "message": alert.message})
    elif drawdown_pct >= DRAWDOWN_WARNING_PCT:
        alert = await _add_alert(
            db,
            session.id,
            AlertType.risk,
            f"WARNING: drawdown {drawdown_pct:.1f}% exceeded {DRAWDOWN_WARNING_PCT}% threshold.",
        )
        events.append({"type": "alert", "alert_type": "risk", "message": alert.message})

    # Emit portfolio snapshot event
    events.append(
        {
            "type": "portfolio_update",
            "equity": equity,
            "cash": session.current_cash,
            "drawdown_pct": drawdown_pct,
        }
    )

    await db.flush()
    return events


async def _execute_signal(
    db: AsyncSession,
    session: PaperTradingSession,
    signal,
    symbol: str,
    current_price: float,
) -> Optional[dict]:
    """Execute a single signal as a paper order. Returns an event dict or None."""
    pos = await _get_or_create_position(db, session.id, symbol)

    if signal.action == "buy":
        # Allocate signal.size fraction of current cash
        alloc = session.current_cash * min(signal.size, 1.0)
        if alloc < current_price * 0.0001:
            # Not enough cash for even a tiny buy
            order = PaperTradingOrder(
                session_id=session.id,
                symbol=symbol,
                action=OrderAction.buy,
                quantity=0,
                price=current_price,
                status=OrderStatus.rejected,
                reject_reason="Insufficient cash",
            )
            db.add(order)
            return None

        commission = alloc * COMMISSION_RATE
        net_alloc = alloc - commission
        qty = net_alloc / current_price

        # Update position (weighted average cost)
        total_qty = pos.quantity + qty
        if total_qty > 0:
            pos.avg_cost = (pos.cost_basis + net_alloc) / total_qty
        pos.quantity = total_qty
        pos.current_price = current_price
        session.current_cash -= alloc

        order = PaperTradingOrder(
            session_id=session.id,
            symbol=symbol,
            action=OrderAction.buy,
            quantity=qty,
            price=current_price,
            commission=commission,
            status=OrderStatus.filled,
        )
        db.add(order)
        return {
            "type": "order",
            "action": "buy",
            "symbol": symbol,
            "quantity": qty,
            "price": current_price,
            "commission": commission,
        }

    elif signal.action == "sell":
        if pos.quantity <= 0:
            return None  # nothing to sell

        qty = pos.quantity * min(signal.size, 1.0)
        gross = qty * current_price
        commission = gross * COMMISSION_RATE
        net_proceeds = gross - commission

        pos.quantity -= qty
        if pos.quantity < 1e-10:
            pos.quantity = 0.0
            pos.avg_cost = 0.0
        pos.current_price = current_price
        session.current_cash += net_proceeds

        order = PaperTradingOrder(
            session_id=session.id,
            symbol=symbol,
            action=OrderAction.sell,
            quantity=qty,
            price=current_price,
            commission=commission,
            status=OrderStatus.filled,
        )
        db.add(order)
        return {
            "type": "order",
            "action": "sell",
            "symbol": symbol,
            "quantity": qty,
            "price": current_price,
            "commission": commission,
        }

    return None
