INSERT INTO crypto.fact_prices
SELECT
    event_time                                        AS snapshot_ts,
    coin_id,
    current_price                                     AS price_usd,
    market_cap,
    toUInt16(ifNull(market_cap_rank, 0))              AS market_cap_rank,
    fully_diluted_valuation,
    total_volume,
    high_24h,
    low_24h,
    price_change_24h,
    price_change_pct_24h,
    market_cap_change_pct_24h,
    circulating_supply,
    total_supply,
    if(max_supply > 0,
       toFloat32(circulating_supply / max_supply),
       NULL)                                          AS supply_ratio,
    ath,
    ath_change_pct,
    toDate(ath_date)                                  AS ath_date,
    atl,
    atl_change_pct,
    toDate(atl_date)                                  AS atl_date,
    now64()                                           AS _ingested_at
FROM s3(
    'http://minio:9000/crypto-lake/silver/crypto.prices/**/*.parquet',
    'minioadmin', 'minioadmin', 'Parquet'
)
WHERE year = {{ logical_date.year }}
    AND month = {{ logical_date.month }}
    AND day = {{ logical_date.day }}
    AND event_time IS NOT NULL
    AND symbol IS NOT NULL;