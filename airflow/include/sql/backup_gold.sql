BACKUP DATABASE crypto_gold TO S3(
        'http://minio:9000/iceberg-lakehouse/warehouse/gold/incremental_backup',
        'minioadmin', 'minioadmin'
    )
SETTINGS base_backup = S3(
    'http://minio:9000/iceberg-lakehouse/warehouse/gold/base_backup',
        'minioadmin', 'minioadmin'
)