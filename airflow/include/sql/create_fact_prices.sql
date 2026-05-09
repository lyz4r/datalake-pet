CREATE TABLE IF NOT EXISTS crypto.fact_prices
(
    snapshot_ts                DateTime64(3, 'UTC'),
    snapshot_date              Date MATERIALIZED toDate(snapshot_ts),
    coin_id                    LowCardinality(String),
    -- цены/объёмы
    price_usd                  Decimal(28, 8),
    market_cap                 Decimal(28, 2),
    market_cap_rank            UInt16,
    fully_diluted_valuation    Nullable(Decimal(28, 2)),
    total_volume               Decimal(28, 2),
    high_24h                   Nullable(Decimal(28, 8)),
    low_24h                    Nullable(Decimal(28, 8)),
    -- изменения 24h
    price_change_24h           Nullable(Decimal(28, 8)),
    price_change_pct_24h       Nullable(Float32),
    market_cap_change_pct_24h  Nullable(Float32),
    -- supply
    circulating_supply         Nullable(Decimal(28, 8)),
    total_supply               Nullable(Decimal(28, 8)),
    supply_ratio               Nullable(Float32),  -- circulating / max
    -- ATH/ATL
    ath                        Nullable(Decimal(28, 8)),
    ath_change_pct             Nullable(Float32),
    ath_date                   Nullable(Date),
    atl                        Nullable(Decimal(28, 8)),
    atl_change_pct             Nullable(Float32),
    atl_date                   Nullable(Date),
    _ingested_at               DateTime64(3) DEFAULT now64()
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(snapshot_ts)
ORDER BY (coin_id, snapshot_ts)
TTL toDate(snapshot_ts) + INTERVAL 1 YEAR;