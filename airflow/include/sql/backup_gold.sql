BACKUP DATABASE crypto_gold TO S3(
        'http://minio:9000/crypto-lake/gold/incremental_backup',
        'minioadmin', 'minioadmin'
    )
SETTINGS base_backup = S3(
    'http://minio:9000/crypto-lake/gold/base_backup',
        'minioadmin', 'minioadmin'
)