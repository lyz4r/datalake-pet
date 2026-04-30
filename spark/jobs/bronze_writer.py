from pyspark.sql import SparkSession
import pyspark.sql.functions as F

PACKAGES = ",".join([
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "com.amazonaws:aws-java-sdk-bundle:1.12.262",
])

spark = (SparkSession.builder
         .appName("dev")
         .master("local[*]")
         .config("spark.jars.packages", PACKAGES)
         .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
         .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
         .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
         .config("spark.hadoop.fs.s3a.path.style.access", "true")
         .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
         .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")


TOPIC = "crypto.tickers"
CHECKPOINT_PATH = f"s3a://spark-checkpoints/bronze{TOPIC}"
BRONZE_PATH = f"s3a://crypto-lake/bronze/{TOPIC}"

source = (spark.readStream.format("kafka")
          .option("kafka.bootstrap.servers", "kafka:9092")
          .option("subscribe", TOPIC)
          .option("startingOffsets", "earliest")
          .load()
          )

parsed = (source.selectExpr("CAST(value AS STRING) as raw_json", "topic", "partition", "offset", "timestamp as kafka_ts")
          .withColumn("ingestion_ts", F.current_timestamp())
          .withColumn("year",  F.year("kafka_ts"))
          .withColumn("month", F.month("kafka_ts"))
          .withColumn("day",   F.dayofmonth("kafka_ts"))
          .withColumn("hour",  F.hour("kafka_ts")))

write = (parsed.writeStream.format("parquet")
         .option("path", BRONZE_PATH)
         .option("checkpointLocation", CHECKPOINT_PATH)
         .partitionBy("year", "month", "day", "hour")
         .trigger(availableNow=True)
         .outputMode("append")
         .start())

write.awaitTermination()
