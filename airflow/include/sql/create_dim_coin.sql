CREATE TABLE IF NOT EXISTS crypto_gold.dim_coin
(
    coin_id            LowCardinality(String),
    symbol             LowCardinality(String),
    name               String,
    image_url          String,
    max_supply         Nullable(Decimal(28, 8)),
    first_seen_date    Date,
    last_seen_date     Date,
    updated_at         DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY coin_id;