from pyspark.sql import SparkSession

def create_session():
    spark = (SparkSession.builder
             .appName("dev")
             .master("local[*]")
             # S3A / MinIO
             .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
             .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
             .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
             .config("spark.hadoop.fs.s3a.path.style.access", "true")
             .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
             .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
             # Iceberg extensions
             .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
             # Iceberg catalog "lake"
             .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
             .config("spark.sql.catalog.lake.type", "hadoop")
             .config("spark.sql.catalog.lake.warehouse", "s3a://iceberg-lakehouse/warehouse")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark
