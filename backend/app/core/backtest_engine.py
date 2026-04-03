"""
Backtest Engine — event-driven simulation with realistic execution modeling.
Phase 1 skeleton; full implementation in Phase 2.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from app.core.strategy import Strategy, Signal


@dataclass
class Trade:
    timestamp: str
    symbol: str
    action: str
    price: float
    size: float
    commission: float
    slippage: float


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    start: str
    end: str
    initial_capital: float
    final_equity: float
    total_return: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)


class BacktestEngine:
    """
    Event-driven backtesting engine.
    - Processes OHLCV bars in sequence
    - Applies slippage and commission models
    - Tracks portfolio state and generates BacktestResult
    """

    def __init__(
        self,
        initial_capital: float = 10_000_000,  # KRW
        commission_rate: float = 0.0005,       # 0.05% per trade
        slippage_rate: float = 0.0002,         # 0.02% market impact
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def run(
        self,
        strategy: Strategy,
        ohlcv: pd.DataFrame,
        symbol: str,
    ) -> BacktestResult:
        """Run a backtest for a given strategy and OHLCV data."""
        signals = strategy.generate_signals(ohlcv)

        capital = self.initial_capital
        position = 0.0
        trades: list[Trade] = []
        equity_curve: list[dict] = []

        signal_map = {s.timestamp: s for s in signals}

        for _, row in ohlcv.iterrows():
            ts = str(row["timestamp"])
            price = float(row["close"])

            if ts in signal_map:
                sig: Signal = signal_map[ts]
                exec_price = price * (
                    1 + self.slippage_rate if sig.action == "buy" else 1 - self.slippage_rate
                )
                if sig.action == "buy" and capital > 0:
                    size = (capital * sig.size) / exec_price
                    commission = size * exec_price * self.commission_rate
                    position += size
                    capital -= size * exec_price + commission
                    trades.append(
                        Trade(ts, symbol, "buy", exec_price, size, commission, exec_price * self.slippage_rate)
                    )
                elif sig.action == "sell" and position > 0:
                    sell_size = position * sig.size
                    commission = sell_size * exec_price * self.commission_rate
                    capital += sell_size * exec_price - commission
                    position -= sell_size
                    trades.append(
                        Trade(ts, symbol, "sell", exec_price, sell_size, commission, exec_price * self.slippage_rate)
                    )

            equity = capital + position * price
            equity_curve.append({"timestamp": ts, "equity": equity})

        final_equity = equity_curve[-1]["equity"] if equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        metrics = self._compute_metrics(equity_curve, trades)

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            start=str(ohlcv.iloc[0]["timestamp"]),
            end=str(ohlcv.iloc[-1]["timestamp"]),
            initial_capital=self.initial_capital,
            final_equity=final_equity,
            total_return=total_return,
            trades=trades,
            equity_curve=equity_curve,
            **metrics,
        )

    def _compute_metrics(self, equity_curve: list[dict], trades: list[Trade]) -> dict:
        if len(equity_curve) < 2:
            return {
                "sharpe_ratio": None,
                "sortino_ratio": None,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
            }

        equities = [e["equity"] for e in equity_curve]
        returns = [(equities[i] - equities[i - 1]) / equities[i - 1] for i in range(1, len(equities))]

        import statistics, math

        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns) if len(returns) > 1 else 0

        sharpe = (mean_r / std_r * math.sqrt(365)) if std_r > 0 else None

        downside = [r for r in returns if r < 0]
        down_std = statistics.stdev(downside) if len(downside) > 1 else 0
        sortino = (mean_r / down_std * math.sqrt(365)) if down_std > 0 else None

        peak = equities[0]
        max_dd = 0.0
        for e in equities:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            if dd > max_dd:
                max_dd = dd

        buy_trades = [t for t in trades if t.action == "buy"]
        sell_trades = [t for t in trades if t.action == "sell"]
        paired = min(len(buy_trades), len(sell_trades))
        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        for i in range(paired):
            pnl = (sell_trades[i].price - buy_trades[i].price) * buy_trades[i].size
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)

        win_rate = wins / paired if paired > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": len(trades),
        }
