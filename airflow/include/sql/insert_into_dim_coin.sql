INSERT INTO crypto_gold.dim_coin
WITH today_data AS (
    SELECT
        coin_id,
        argMax(symbol, event_time)     AS symbol,
        argMax(name, event_time)       AS name,
        argMax(image_url, event_time)  AS image_url,
        argMax(max_supply, event_time) AS max_supply,
        toDate(min(event_time))        AS today_first,
        toDate(max(event_time))        AS today_last
    FROM icebergS3(
    'http://minio:9000/iceberg-lakehouse/warehouse/silver/prices/',
    'minioadmin', 'minioadmin', 'Parquet'
    )
    WHERE year  = {{ logical_date.year }}
      AND month = {{ logical_date.month }}
      AND day   = {{ logical_date.day }}
      AND event_time IS NOT NULL
    GROUP BY coin_id
    HAVING symbol IS NOT NULL
),
existing AS (
    SELECT coin_id, min(first_seen_date) AS first_seen_date
    FROM crypto_gold.dim_coin FINAL
    GROUP BY coin_id
)
SELECT
    t.coin_id,
    t.symbol,
    t.name,
    t.image_url,
    t.max_supply,
    ifNull(e.first_seen_date, t.today_first) AS first_seen_date,
    t.today_last                             AS last_seen_date,
    now()                                    AS updated_at
FROM today_data t
LEFT JOIN existing e USING (coin_id);