-- PRISM Data Layer — TimescaleDB Schema
-- Run with: psql $DATABASE_URL -f schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─────────────────────────────────────────────────────────────────────────────
-- OHLCV candles  (1m, 3m, 5m, 15m, 60m, 240m, 1D, 1W)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candles (
    time        TIMESTAMPTZ     NOT NULL,
    market      TEXT            NOT NULL,   -- e.g. "KRW-BTC"
    interval    TEXT            NOT NULL,   -- "1","3","5","15","60","240","D","W"
    open        NUMERIC(24, 8)  NOT NULL,
    high        NUMERIC(24, 8)  NOT NULL,
    low         NUMERIC(24, 8)  NOT NULL,
    close       NUMERIC(24, 8)  NOT NULL,
    volume      NUMERIC(32, 8)  NOT NULL,   -- base currency volume
    quote_volume NUMERIC(32, 2) NOT NULL,   -- KRW volume
    trade_count INTEGER,
    PRIMARY KEY (time, market, interval)
);

SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

-- Continuous aggregate for hourly rollup from 1m candles
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    market,
    first(open, time)       AS open,
    max(high)               AS high,
    min(low)                AS low,
    last(close, time)       AS close,
    sum(volume)             AS volume,
    sum(quote_volume)       AS quote_volume,
    sum(trade_count)        AS trade_count
FROM candles
WHERE interval = '1'
GROUP BY bucket, market;

-- ─────────────────────────────────────────────────────────────────────────────
-- Order book snapshots
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    time            TIMESTAMPTZ     NOT NULL,
    market          TEXT            NOT NULL,
    total_ask_size  NUMERIC(32, 8),
    total_bid_size  NUMERIC(32, 8),
    PRIMARY KEY (time, market)
);

SELECT create_hypertable('orderbook_snapshots', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS orderbook_units (
    time        TIMESTAMPTZ     NOT NULL,
    market      TEXT            NOT NULL,
    side        TEXT            NOT NULL,   -- 'ask' | 'bid'
    price       NUMERIC(24, 8)  NOT NULL,
    size        NUMERIC(32, 8)  NOT NULL,
    PRIMARY KEY (time, market, side, price)
);

SELECT create_hypertable('orderbook_units', 'time', if_not_exists => TRUE);

-- ─────────────────────────────────────────────────────────────────────────────
-- Individual trades (tick data)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
    time                TIMESTAMPTZ     NOT NULL,
    market              TEXT            NOT NULL,
    trade_id            TEXT,
    price               NUMERIC(24, 8)  NOT NULL,
    volume              NUMERIC(32, 8)  NOT NULL,
    side                TEXT            NOT NULL,   -- 'ASK' | 'BID'
    prev_closing_price  NUMERIC(24, 8),
    change_price        NUMERIC(24, 8),
    PRIMARY KEY (time, market, trade_id)
);

SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);

-- ─────────────────────────────────────────────────────────────────────────────
-- Data quality audit log
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_quality_log (
    id          BIGSERIAL       PRIMARY KEY,
    logged_at   TIMESTAMPTZ     DEFAULT NOW(),
    market      TEXT            NOT NULL,
    interval    TEXT,
    issue_type  TEXT            NOT NULL,   -- 'missing', 'outlier', 'stale', 'gap'
    detail      JSONB,
    resolved    BOOLEAN         DEFAULT FALSE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Backfill tracking
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backfill_jobs (
    id          BIGSERIAL       PRIMARY KEY,
    market      TEXT            NOT NULL,
    interval    TEXT            NOT NULL,
    from_time   TIMESTAMPTZ     NOT NULL,
    to_time     TIMESTAMPTZ     NOT NULL,
    status      TEXT            NOT NULL DEFAULT 'pending',  -- pending/running/done/failed
    rows_written INTEGER,
    error       TEXT,
    created_at  TIMESTAMPTZ     DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Korean stocks — OHLCV candles (Phase 2: KIS)
-- ticker: 6-digit KRX code (e.g. "005930" = Samsung Electronics)
-- market_div: "J" = KOSPI, "Q" = KOSDAQ
-- interval: "1","5","15","30","60","D"
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_candles (
    time        TIMESTAMPTZ     NOT NULL,
    ticker      TEXT            NOT NULL,
    market_div  TEXT            NOT NULL,
    interval    TEXT            NOT NULL,
    open        NUMERIC(20, 0)  NOT NULL,   -- KRW (no fractional won)
    high        NUMERIC(20, 0)  NOT NULL,
    low         NUMERIC(20, 0)  NOT NULL,
    close       NUMERIC(20, 0)  NOT NULL,
    volume      BIGINT          NOT NULL,
    trade_value NUMERIC(32, 0)  NOT NULL DEFAULT 0,  -- 거래대금 (KRW)
    PRIMARY KEY (time, ticker, interval)
);

SELECT create_hypertable('stock_candles', 'time', if_not_exists => TRUE);

-- ─────────────────────────────────────────────────────────────────────────────
-- KOSPI 200 constituents
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kospi200_constituents (
    ticker      TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    sector      TEXT    NOT NULL DEFAULT '',
    market_div  TEXT    NOT NULL DEFAULT 'J',
    added_date  DATE    NOT NULL,
    removed_date DATE,
    PRIMARY KEY (ticker, added_date)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Backfill tracking — Korean stocks
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_backfill_jobs (
    id          BIGSERIAL       PRIMARY KEY,
    ticker      TEXT            NOT NULL,
    interval    TEXT            NOT NULL,
    from_time   TIMESTAMPTZ     NOT NULL,
    to_time     TIMESTAMPTZ     NOT NULL,
    status      TEXT            NOT NULL DEFAULT 'pending',
    rows_written INTEGER,
    error       TEXT,
    created_at  TIMESTAMPTZ     DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_candles_market_interval ON candles (market, interval, time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades (market, time DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_market ON orderbook_snapshots (market, time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_candles_ticker_interval ON stock_candles (ticker, interval, time DESC);
CREATE INDEX IF NOT EXISTS idx_kospi200_ticker ON kospi200_constituents (ticker);
