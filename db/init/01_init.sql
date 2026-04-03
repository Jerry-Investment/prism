-- PRISM Database Initialization
-- PostgreSQL + TimescaleDB

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ─────────────────────────────────────────
-- Market Data
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ohlcv (
    time        TIMESTAMPTZ     NOT NULL,
    symbol      TEXT            NOT NULL,
    source      TEXT            NOT NULL DEFAULT 'upbit',  -- upbit | kis | yahoo
    interval    TEXT            NOT NULL DEFAULT '1d',     -- 1m, 5m, 15m, 1h, 4h, 1d
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (time, symbol, source, interval)
);

-- Convert to TimescaleDB hypertable (partitioned by time)
SELECT create_hypertable('ohlcv', 'time', if_not_exists => TRUE);

-- Compression policy: compress chunks older than 7 days
SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);

-- Continuous aggregate: daily OHLCV from 1m data
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    source,
    FIRST(open, time)  AS open,
    MAX(high)          AS high,
    MIN(low)           AS low,
    LAST(close, time)  AS close,
    SUM(volume)        AS volume
FROM ohlcv
WHERE interval = '1m'
GROUP BY bucket, symbol, source
WITH NO DATA;

-- ─────────────────────────────────────────
-- Strategies
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS strategies (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT            NOT NULL,
    description TEXT            DEFAULT '',
    type        TEXT            NOT NULL,  -- ma_cross | rsi | volume | custom
    parameters  JSONB           NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- Backtests
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS backtests (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     UUID            REFERENCES strategies(id) ON DELETE SET NULL,
    symbol          TEXT            NOT NULL,
    interval        TEXT            NOT NULL DEFAULT '1d',
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    initial_capital DOUBLE PRECISION NOT NULL,
    final_equity    DOUBLE PRECISION,
    total_return    DOUBLE PRECISION,
    sharpe_ratio    DOUBLE PRECISION,
    sortino_ratio   DOUBLE PRECISION,
    max_drawdown    DOUBLE PRECISION,
    win_rate        DOUBLE PRECISION,
    profit_factor   DOUBLE PRECISION,
    total_trades    INTEGER,
    status          TEXT            NOT NULL DEFAULT 'pending',  -- pending | running | done | failed
    error_message   TEXT,
    celery_task_id  TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- ─────────────────────────────────────────
-- Trades (backtest simulation results)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS backtest_trades (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_id     UUID            NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    time            TIMESTAMPTZ     NOT NULL,
    symbol          TEXT            NOT NULL,
    action          TEXT            NOT NULL,  -- buy | sell
    price           DOUBLE PRECISION NOT NULL,
    size            DOUBLE PRECISION NOT NULL,
    commission      DOUBLE PRECISION NOT NULL DEFAULT 0,
    slippage        DOUBLE PRECISION NOT NULL DEFAULT 0,
    pnl             DOUBLE PRECISION
);

SELECT create_hypertable('backtest_trades', 'time', if_not_exists => TRUE);

-- ─────────────────────────────────────────
-- Equity Curve (backtest)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS equity_curve (
    time        TIMESTAMPTZ     NOT NULL,
    backtest_id UUID            NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    equity      DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (time, backtest_id)
);

SELECT create_hypertable('equity_curve', 'time', if_not_exists => TRUE);

-- ─────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_interval ON ohlcv (symbol, interval, time DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_backtest ON backtest_trades (backtest_id, time);
CREATE INDEX IF NOT EXISTS idx_equity_curve_backtest ON equity_curve (backtest_id, time);
