INSERT INTO crypto_gold.fact_tickers (
        bucket_start,
        symbol,
        open_price,
        high_price,
        low_price,
        close_price,
        volume_24h,
        tickers_count
    )
SELECT toStartOfMinute(event_time) as bucket_start,
    symbol,
    argMin(last_price, event_time) as open_price,
    max(last_price) as high_price,
    min(last_price) as low_price,
    argMax(last_price, event_time) as close_price,
    argMax(volume_24h, event_time) as volume_24h,
    count() as tickers_count
FROM crypto.silver_tickers_s3
WHERE year = {{ logical_date.year }}
    AND month = {{ logical_date.month }}
    AND day = {{ logical_date.day }}
    AND event_time IS NOT NULL
    AND symbol IS NOT NULL
GROUP BY symbol,
    bucket_start;