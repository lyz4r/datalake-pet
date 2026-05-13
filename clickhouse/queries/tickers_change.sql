SELECT
    toStartOfMinute(event_time) AS bucket_start,
    max(last_price) AS max_bucket_price,
    min(last_price) AS min_bucket_price,
    argMin(last_price, event_time) AS first_bucket_price,
    argMax(last_price, event_time) AS last_bucket_price
FROM s3(
    'http://minio:9000/crypto-lake/silver/crypto.tickers/**/*.parquet',
    'minioadmin', 'minioadmin', 'Parquet'
)
WHERE year = toYear(now()) AND month = toMonth(now()) AND day = toDayOfMonth(now())
GROUP BY bucket_start
ORDER BY bucket_start;