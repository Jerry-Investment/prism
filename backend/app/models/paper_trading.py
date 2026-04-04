from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.session import Base


class SessionStatus(str, enum.Enum):
    active = "active"
    stopped = "stopped"
    paused = "paused"


class OrderAction(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderStatus(str, enum.Enum):
    filled = "filled"
    rejected = "rejected"
    pending = "pending"


class AlertType(str, enum.Enum):
    signal = "signal"
    risk = "risk"
    info = "info"


class PaperTradingSession(Base):
    __tablename__ = "paper_trading_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strategy_id = Column(String, nullable=False)
    strategy_params = Column(String, nullable=True)  # JSON string
    symbols = Column(String, nullable=False)          # comma-separated, e.g. "KRW-BTC,KRW-ETH"
    interval = Column(String, default="1d")
    initial_capital = Column(Float, nullable=False)
    current_cash = Column(Float, nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.active, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    positions = relationship("PaperTradingPosition", back_populates="session", cascade="all, delete-orphan")
    orders = relationship("PaperTradingOrder", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("PaperTradingAlert", back_populates="session", cascade="all, delete-orphan")

    @property
    def symbol_list(self) -> list[str]:
        return [s.strip() for s in self.symbols.split(",") if s.strip()]


class PaperTradingPosition(Base):
    __tablename__ = "paper_trading_positions"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("paper_trading_sessions.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    quantity = Column(Float, default=0.0)
    avg_cost = Column(Float, default=0.0)       # average cost per unit
    current_price = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("PaperTradingSession", back_populates="positions")

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


class PaperTradingOrder(Base):
    __tablename__ = "paper_trading_orders"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("paper_trading_sessions.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    action = Column(Enum(OrderAction), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    reject_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("PaperTradingSession", back_populates="orders")


class PaperTradingAlert(Base):
    __tablename__ = "paper_trading_alerts"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("paper_trading_sessions.id"), nullable=False, index=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    message = Column(String, nullable=False)
    symbol = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("PaperTradingSession", back_populates="alerts")
