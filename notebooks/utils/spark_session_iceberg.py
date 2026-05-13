from pyspark.sql import SparkSession

_PACKAGES = ",".join([
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2",
])


def createSpark():
    spark = (SparkSession.builder
             .appName("dev")
             .master("local[*]")
             .config("spark.jars.packages", _PACKAGES)
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
