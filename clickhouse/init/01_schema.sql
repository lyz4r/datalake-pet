CREATE DATABASE IF NOT EXISTS crypto;
CREATE TABLE IF NOT EXISTS crypto.kafka_tickers (raw String) ENGINE = Kafka SETTINGS kafka_broker_list = 'kafka:9092',
kafka_topic_list = 'crypto.tickers',
kafka_group_name = 'clickhouse_tickers_consumer',
kafka_format = 'JSONAsString',
kafka_num_consumers = 2,
kafka_skip_broken_messages = 100;
CREATE TABLE IF NOT EXISTS crypto.raw_tickers (
    event_time DateTime64(3, 'UTC'),
    symbol LowCardinality(String),
    exchange LowCardinality(String) DEFAULT 'bybit',
    msg_type LowCardinality(String),
    last_price Nullable(Decimal(18, 8)),
    high_price_24h Nullable(Decimal(18, 8)),
    low_price_24h Nullable(Decimal(18, 8)),
    prev_price_24h Nullable(Decimal(18, 8)),
    volume_24h Nullable(Decimal(28, 8)),
    turnover_24h Nullable(Decimal(28, 8)),
    price_24h_pcnt Nullable(Float32),
    usd_index_price Nullable(Decimal(18, 8)),
    cross_seq UInt64,
    ingestion_ts DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(ingestion_ts) PARTITION BY toYYYYMMDD(event_time)
ORDER BY (symbol, event_time, cross_seq) TTL toDate(event_time) + INTERVAL 90 DAY;
CREATE MATERIALIZED VIEW IF NOT EXISTS crypto.kafka_to_raw_tickers TO crypto.raw_tickers AS
SELECT fromUnixTimestamp64Milli(JSONExtractUInt(raw, 'ts')) AS event_time,
    JSONExtractString(raw, 'data', 'symbol') AS symbol,
    'bybit' AS exchange,
    JSONExtractString(raw, 'type') AS msg_type,
    toDecimal64OrNull(JSONExtractString(raw, 'data', 'lastPrice'), 8) AS last_price,
    toDecimal64OrNull(
        JSONExtractString(raw, 'data', 'highPrice24h'),
        8
    ) AS high_price_24h,
    toDecimal64OrNull(JSONExtractString(raw, 'data', 'lowPrice24h'), 8) AS low_price_24h,
    toDecimal64OrNull(
        JSONExtractString(raw, 'data', 'prevPrice24h'),
        8
    ) AS prev_price_24h,
    toDecimal64OrNull(JSONExtractString(raw, 'data', 'volume24h'), 8) AS volume_24h,
    toDecimal64OrNull(JSONExtractString(raw, 'data', 'turnover24h'), 8) AS turnover_24h,
    toFloat32OrNull(JSONExtractString(raw, 'data', 'price24hPcnt')) AS price_24h_pcnt,
    toDecimal64OrNull(
        JSONExtractString(raw, 'data', 'usdIndexPrice'),
        8
    ) AS usd_index_price,
    JSONExtractUInt(raw, 'cs') AS cross_seq,
    now64(3) AS ingestion_ts
FROM crypto.kafka_tickers;