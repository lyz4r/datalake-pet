from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("S3_to_ClickHouse").getOrCreate()

default_folders = ['batch_output', 'kafka_output', 'generate'] # для удобства
bucket_folder = 'batch_output'
# Читаем паркеты из MinIO
df = spark.read.parquet(f"s3a://bucket/{bucket_folder}/")

# JDBC параметры ClickHouse (HTTP-порт 8123)
clickhouse_url = "jdbc:clickhouse://clickhouse:8123/default"
target_table = "new_table"

(
    df.write
      .format("jdbc")
      .option("url", clickhouse_url)
      .option("dbtable", target_table)
      .option("driver", "com.clickhouse.jdbc.ClickHouseDriver")
      .option("createTableOptions", "ENGINE=MergeTree ORDER BY tuple()")
      .option("batchsize", "10000")
      .mode("append")
      .save()
)

spark.stop()
