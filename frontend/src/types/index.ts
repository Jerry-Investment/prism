export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  type: "ma_cross" | "rsi" | "volume" | "custom";
  parameters: Record<string, unknown>;
}

export interface BacktestRequest {
  strategy_id: string;
  symbol: string;
  interval: string;
  start: string;
  end: string;
  initial_capital: number;
  params?: Record<string, unknown>;
}

// Paper Trading types
export interface PaperTradingSessionSummary {
  id: number;
  strategy_id: string;
  symbols: string;
  status: "active" | "stopped" | "paused";
  initial_capital: number;
  current_cash: number;
  equity: number;
  total_return_pct: number;
  created_at: string;
}

export interface PaperTradingPosition {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface PaperTradingOrder {
  id: number;
  symbol: string;
  action: "buy" | "sell";
  quantity: number;
  price: number;
  commission: number;
  status: "filled" | "rejected" | "pending";
  reject_reason?: string;
  created_at: string;
}

export interface PaperTradingAlert {
  id: number;
  alert_type: "signal" | "risk" | "info";
  message: string;
  symbol?: string;
  is_read: boolean;
  created_at: string;
}

export interface BacktestResult {
  strategy_name: string;
  symbol: string;
  start: string;
  end: string;
  initial_capital: number;
  final_equity: number;
  total_return: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  equity_curve: Array<{ timestamp: string; equity: number }>;
}
