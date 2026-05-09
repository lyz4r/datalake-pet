CREATE TABLE IF NOT EXISTS crypto.fact_tickers(
    bucket_start DateTime64(9),
    symbol LowCardinality(String),
    open_price DECIMAL(18, 8),
    high_price DECIMAL(18, 8),
    low_price DECIMAL(18, 8),
    close_price DECIMAL(18, 8),
    volume_24h DECIMAL(22, 4),
    tickers_count UInt32,
    inserted_at DateTime64 DEFAULT now()
) ENGINE = ReplacingMergeTree() PARTITION BY toYYYYMM(bucket_start)
ORDER BY (symbol, bucket_start) TTL bucket_start + INTERVAL 1 YEAR