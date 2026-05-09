SELECT coin_id,
    bucket_start,
    max_price,
    argMax(max_price, bucket_start) OVER (PARTITION BY coin_id) - argMin(max_price, bucket_start) OVER (PARTITION BY coin_id) AS change_7d,
    change_7d / argMin(max_price, bucket_start) OVER (PARTITION BY coin_id) AS change_7d_pct
FROM s3(
        'http://minio:9000/crypto-lake/gold/crypto.prices/**/*.parquet',
        'minioadmin',
        'minioadmin',
        'Parquet'
    )
WHERE bucket_start >= now() - INTERVAL 7 DAY
ORDER BY change_7d_pct DESC,
    bucket_start DESC;