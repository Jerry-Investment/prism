"""
Backtest Engine — Phase 2: event-driven simulation with realistic execution modeling.

Features:
- Event-driven bar-by-bar simulation
- Multi-asset portfolio management
- Slippage and commission modeling
- Benchmark (buy-and-hold) comparison per symbol
- Progress callback support
"""

import sys
import os

# Make prism importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import math
import statistics
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import pandas as pd


@dataclass
class Trade:
    timestamp: str
    symbol: str
    action: str        # "buy" | "sell"
    price: float
    size: float
    commission: float
    slippage: float


@dataclass
class BenchmarkResult:
    name: str
    symbol: str
    total_return: float
    sharpe_ratio: Optional[float]
    max_drawdown: float


@dataclass
class PortfolioState:
    cash: float
    positions: Dict[str, float] = field(default_factory=dict)  # symbol → qty

    def equity(self, prices: Dict[str, float]) -> float:
        pos_value = sum(self.positions.get(sym, 0.0) * p for sym, p in prices.items())
        return self.cash + pos_value


@dataclass
class BacktestResult:
    strategy_name: str
    # keep original single-symbol field for backward compat
    symbol: str
    symbols: List[str]
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
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    benchmarks: List[BenchmarkResult] = field(default_factory=list)


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Processes bars in chronological order across all symbols, calls the
    strategy at each step, executes signals with slippage/commission,
    and tracks portfolio state.
    """

    def __init__(
        self,
        initial_capital: float = 10_000_000,   # KRW
        commission_rate: float = 0.0005,        # 0.05% per trade
        slippage_rate: float = 0.0002,          # 0.02% market impact
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        strategy,
        data: Dict[str, pd.DataFrame],
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> BacktestResult:
        """
        Run a full backtest.

        Args:
            strategy:    A prism Strategy instance.
            data:        Dict of symbol → OHLCV DataFrame with DatetimeIndex (UTC).
            progress_cb: Optional callable receiving progress pct in [0, 100].

        Returns:
            BacktestResult with all metrics, trades, equity curve, and benchmarks.
        """
        symbols = list(data.keys())

        # Build unified sorted timestamp index across all symbols
        all_ts = pd.DatetimeIndex(
            sorted(set().union(*[df.index.tolist() for df in data.values()]))
        )
        n_bars = len(all_ts)

        portfolio = PortfolioState(cash=self.initial_capital)
        trades: List[Trade] = []
        equity_curve: List[dict] = []

        strategy.on_start(data)

        for bar_idx, ts in enumerate(all_ts):
            # Build data window: all bars up to and including current ts
            data_window: Dict[str, pd.DataFrame] = {}
            prices: Dict[str, float] = {}

            for sym, df in data.items():
                window = df.loc[df.index <= ts]
                if not window.empty:
                    data_window[sym] = window
                    prices[sym] = float(window["close"].iloc[-1])

            if not data_window:
                continue

            # Generate signals from strategy with current window
            try:
                signals = strategy.generate_signals(data_window)
            except Exception:
                signals = []

            # Execute each signal
            for sig in signals:
                from prism.strategy.base import SignalDirection
                sym = sig.asset
                if sym not in prices:
                    continue

                if sig.direction == SignalDirection.BUY:
                    trade = self._execute_buy(sig, prices, portfolio, ts)
                    if trade:
                        trades.append(trade)
                elif sig.direction == SignalDirection.SELL:
                    trade = self._execute_sell(sig, prices, portfolio, ts)
                    if trade:
                        trades.append(trade)

            # Record equity snapshot
            current_equity = portfolio.equity(prices)
            equity_curve.append({"timestamp": ts.isoformat(), "equity": current_equity})

            # Progress callback
            if progress_cb and n_bars > 0:
                pct = ((bar_idx + 1) / n_bars) * 50.0 + 50.0  # maps to 50–100%
                progress_cb(min(pct, 100.0))

        strategy.on_end()

        # Final equity
        final_prices: Dict[str, float] = {}
        for sym, df in data.items():
            if not df.empty:
                final_prices[sym] = float(df["close"].iloc[-1])

        final_equity = portfolio.equity(final_prices)
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        metrics = self._compute_metrics(equity_curve, trades)

        # Benchmarks: buy-and-hold for each symbol
        benchmarks: List[BenchmarkResult] = []
        for sym, df in data.items():
            bm = self._compute_benchmark(f"{sym} Buy & Hold", sym, df)
            benchmarks.append(bm)

        # Determine start/end from equity curve
        start_ts = equity_curve[0]["timestamp"] if equity_curve else ""
        end_ts = equity_curve[-1]["timestamp"] if equity_curve else ""

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbols[0] if symbols else "",
            symbols=symbols,
            start=start_ts,
            end=end_ts,
            initial_capital=self.initial_capital,
            final_equity=final_equity,
            total_return=total_return,
            trades=trades,
            equity_curve=equity_curve,
            benchmarks=benchmarks,
            **metrics,
        )

    # ------------------------------------------------------------------
    # Order execution helpers
    # ------------------------------------------------------------------

    def _execute_buy(
        self,
        signal,
        prices: Dict[str, float],
        portfolio: PortfolioState,
        ts: pd.Timestamp,
    ) -> Optional[Trade]:
        sym = signal.asset
        base_price = prices[sym]
        # Apply positive slippage on buys (pay more)
        exec_price = base_price * (1.0 + self.slippage_rate)

        # Size: use strategy's position_fraction param if available, else signal strength
        fraction = signal.strength  # strength already encodes desired fraction via sizer
        notional = portfolio.cash * fraction
        if notional <= 0:
            return None

        commission = notional * self.commission_rate
        total_cost = notional + commission
        if total_cost > portfolio.cash:
            # Scale down to available cash
            notional = portfolio.cash / (1.0 + self.commission_rate)
            commission = notional * self.commission_rate
            total_cost = notional + commission

        if notional <= 0:
            return None

        qty = notional / exec_price
        portfolio.cash -= total_cost
        portfolio.positions[sym] = portfolio.positions.get(sym, 0.0) + qty

        return Trade(
            timestamp=ts.isoformat(),
            symbol=sym,
            action="buy",
            price=exec_price,
            size=qty,
            commission=commission,
            slippage=base_price * self.slippage_rate * qty,
        )

    def _execute_sell(
        self,
        signal,
        prices: Dict[str, float],
        portfolio: PortfolioState,
        ts: pd.Timestamp,
    ) -> Optional[Trade]:
        sym = signal.asset
        held_qty = portfolio.positions.get(sym, 0.0)
        if held_qty <= 0:
            return None

        base_price = prices[sym]
        # Apply negative slippage on sells (receive less)
        exec_price = base_price * (1.0 - self.slippage_rate)

        sell_qty = held_qty * signal.strength
        if sell_qty <= 0:
            return None

        gross = sell_qty * exec_price
        commission = gross * self.commission_rate
        net_proceeds = gross - commission

        portfolio.cash += net_proceeds
        portfolio.positions[sym] = held_qty - sell_qty
        if portfolio.positions[sym] < 1e-12:
            portfolio.positions[sym] = 0.0

        return Trade(
            timestamp=ts.isoformat(),
            symbol=sym,
            action="sell",
            price=exec_price,
            size=sell_qty,
            commission=commission,
            slippage=base_price * self.slippage_rate * sell_qty,
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _compute_metrics(self, equity_curve: List[dict], trades: List[Trade]) -> dict:
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
        returns = [
            (equities[i] - equities[i - 1]) / equities[i - 1]
            for i in range(1, len(equities))
        ]

        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns) if len(returns) > 1 else 0.0

        sharpe = (mean_r / std_r * math.sqrt(365)) if std_r > 0 else None

        downside = [r for r in returns if r < 0]
        down_std = statistics.stdev(downside) if len(downside) > 1 else 0.0
        sortino = (mean_r / down_std * math.sqrt(365)) if down_std > 0 else None

        # Max drawdown
        peak = equities[0]
        max_dd = 0.0
        for e in equities:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Win rate and profit factor (pair buy→sell trades per symbol)
        buy_trades: Dict[str, List[Trade]] = {}
        sell_trades: Dict[str, List[Trade]] = {}
        for t in trades:
            if t.action == "buy":
                buy_trades.setdefault(t.symbol, []).append(t)
            else:
                sell_trades.setdefault(t.symbol, []).append(t)

        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        pairs = 0

        for sym in set(list(buy_trades.keys()) + list(sell_trades.keys())):
            buys = buy_trades.get(sym, [])
            sells = sell_trades.get(sym, [])
            paired = min(len(buys), len(sells))
            pairs += paired
            for i in range(paired):
                pnl = (sells[i].price - buys[i].price) * buys[i].size
                if pnl > 0:
                    wins += 1
                    gross_profit += pnl
                else:
                    gross_loss += abs(pnl)

        win_rate = wins / pairs if pairs > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": len(trades),
        }

    def _compute_benchmark(
        self,
        name: str,
        symbol: str,
        df: pd.DataFrame,
    ) -> BenchmarkResult:
        """Compute buy-and-hold benchmark for a single symbol."""
        if df.empty or len(df) < 2:
            return BenchmarkResult(
                name=name,
                symbol=symbol,
                total_return=0.0,
                sharpe_ratio=None,
                max_drawdown=0.0,
            )

        closes = df["close"].tolist()
        start_price = closes[0]
        end_price = closes[-1]
        total_return = (end_price - start_price) / start_price if start_price > 0 else 0.0

        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
        ]

        mean_r = statistics.mean(returns) if returns else 0.0
        std_r = statistics.stdev(returns) if len(returns) > 1 else 0.0
        sharpe = (mean_r / std_r * math.sqrt(365)) if std_r > 0 else None

        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return BenchmarkResult(
            name=name,
            symbol=symbol,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
        )
