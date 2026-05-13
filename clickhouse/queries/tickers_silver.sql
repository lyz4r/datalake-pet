CREATE TABLE crypto.silver_tickers_s3 (
    ingestion_ts Nullable(DateTime64(9)),
    kafka_ts Nullable(DateTime64(9)),
    event_time Nullable(DateTime64(9)),
    type Nullable(String),
    cs Nullable(Int64),
    symbol Nullable(String),
    last_price Nullable(Decimal(18, 8)),
    high_price_24h Nullable(Decimal(18, 8)),
    low_price_24h Nullable(Decimal(18, 8)),
    prev_price_24h Nullable(Decimal(18, 8)),
    volume_24h Nullable(Decimal(22, 4)),
    turnover_24h Nullable(Decimal(22, 4)),
    price_24h_pct Nullable(Decimal(10, 6)),
    usd_index_price Nullable(Decimal(18, 8)),
    day Int64,
    month Int64,
    year Int64
) ENGINE = S3(
    'http://minio:9000/crypto-lake/silver/crypto.tickers/**/*.parquet',
    'minioadmin',
    'minioadmin',
    'Parquet'
) SETTINGS use_hive_partitioning = 1;