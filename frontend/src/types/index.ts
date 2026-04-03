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
