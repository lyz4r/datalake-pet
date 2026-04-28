-- CryptoFlow MVP — ClickHouse schema
-- Runs once on first container start (mounted into /docker-entrypoint-initdb.d/)

CREATE DATABASE IF NOT EXISTS crypto;

-- ============================================================================
-- PHASE 3: Hot path  Kafka -> ClickHouse  (no Spark needed)
-- Uses Kafka engine + materialized view pattern
-- ============================================================================

-- Step 1: persistent storage table (where we actually query)
CREATE TABLE IF NOT EXISTS crypto.raw_tickers
(
    event_time      DateTime64(3, 'UTC'),
    symbol          LowCardinality(String),
    exchange        LowCardinality(String) DEFAULT 'binance',
    price           Decimal(18, 8),
    volume_24h      Decimal(22, 4),
    price_change    Float32,
    bid_price       Decimal(18, 8),
    ask_price       Decimal(18, 8),
    ingestion_ts    DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(event_time)
ORDER BY (symbol, event_time)
TTL toDate(event_time) + INTERVAL 90 DAY;

-- Step 2: Kafka engine table — virtual queue, NOT for direct querying
CREATE TABLE IF NOT EXISTS crypto.kafka_tickers
(
    event_time      DateTime64(3, 'UTC'),
    symbol          String,
    exchange        String,
    price           Float64,
    volume_24h      Float64,
    price_change    Float32,
    bid_price       Float64,
    ask_price       Float64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list           = 'kafka:9092',
    kafka_topic_list            = 'crypto.tickers',
    kafka_group_name            = 'clickhouse_tickers_consumer',
    kafka_format                = 'JSONEachRow',
    kafka_num_consumers         = 2,
    kafka_max_block_size        = 1048576,
    kafka_skip_broken_messages  = 100;

-- Step 3: Materialized view auto-pulls from Kafka into raw_tickers
CREATE MATERIALIZED VIEW IF NOT EXISTS crypto.mv_kafka_to_tickers
TO crypto.raw_tickers
AS
SELECT
    event_time,
    symbol,
    exchange,
    toDecimal64(price, 8)        AS price,
    toDecimal64(volume_24h, 4)   AS volume_24h,
    price_change,
    toDecimal64(bid_price, 8)    AS bid_price,
    toDecimal64(ask_price, 8)    AS ask_price,
    now64(3)                     AS ingestion_ts
FROM crypto.kafka_tickers;

-- ============================================================================
-- PHASE 5+: OHLCV (filled by CoinGecko OHLC producer via Airflow)
-- ============================================================================

CREATE TABLE IF NOT EXISTS crypto.raw_ohlcv
(
    open_time     DateTime64(3, 'UTC'),
    symbol        LowCardinality(String),
    timeframe     LowCardinality(String),  -- '1m', '5m', '1h', '1d'
    open          Decimal(18, 8),
    high          Decimal(18, 8),
    low           Decimal(18, 8),
    close         Decimal(18, 8),
    volume        Decimal(22, 4),
    ingestion_ts  DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(ingestion_ts)
PARTITION BY toYYYYMM(open_time)
ORDER BY (symbol, timeframe, open_time);

-- ============================================================================
-- PHASE 5+: Sentiment (Fear & Greed Index, daily)
-- ============================================================================

CREATE TABLE IF NOT EXISTS crypto.fear_greed
(
    date              Date,
    value             UInt8,           -- 0..100
    classification    LowCardinality(String),
    ingestion_ts      DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(ingestion_ts)
ORDER BY date;

-- ============================================================================
-- PHASE 7+: Aggregated metrics produced by Spark Gold job
-- ============================================================================

CREATE TABLE IF NOT EXISTS crypto.asset_metrics
(
    metric_hour       DateTime,
    symbol            LowCardinality(String),
    price_open        Decimal(28, 8),
    price_high        Decimal(28, 8),
    price_low         Decimal(28, 8),
    price_close       Decimal(28, 8),
    volume_total      Decimal(28, 4),
    sma_20            Nullable(Float64),
    rsi_14            Nullable(Float32),
    price_change_1h   Float32,
    price_change_24h  Float32,
    fear_greed_index  Nullable(UInt8),
    updated_at        DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(metric_hour)
ORDER BY (symbol, metric_hour)
TTL metric_hour + INTERVAL 2 YEAR;

-- ============================================================================
-- Helpful views
-- ============================================================================

CREATE VIEW IF NOT EXISTS crypto.v_latest_prices AS
SELECT
    symbol,
    argMax(price, event_time) AS price,
    max(event_time)           AS as_of
FROM crypto.raw_tickers
WHERE event_time > now() - INTERVAL 5 MINUTE
GROUP BY symbol
ORDER BY price DESC;
