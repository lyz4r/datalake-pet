import logging
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, DecimalType, LongType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("silver_processor")

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

df = spark.read.parquet("s3a://crypto-lake/bronze/crypto.tickers/")
bronze_schema = df.schema  # сериализованная схема, господи прости


TOPIC = "crypto.tickers"
CHECKPOINT_BRONZE_PATH = f"s3a://spark-checkpoints/bronze/{TOPIC}"
CHECKPOINT_SILVER_PATH = f"s3a://spark-checkpoints/silver/{TOPIC}"
BRONZE_PATH = f"s3a://crypto-lake/bronze/{TOPIC}"
SILVER_PATH = f"s3a://crypto-lake/silver/{TOPIC}"

# схема вложенной структуры полезной нагрузки
data_schema = StructType([
    StructField("symbol", StringType(), True),
    StructField("lastPrice", StringType(), True),
    StructField("highPrice24h", StringType(), True),
    StructField("lowPrice24h", StringType(), True),
    StructField("prevPrice24h", StringType(), True),
    StructField("volume24h", StringType(), True),
    StructField("turnover24h", StringType(), True),
    StructField("price24hPcnt", StringType(), True),
    StructField("usdIndexPrice", StringType(), True),
])

payload_schema = StructType([
    StructField("ts", LongType(), True),
    StructField("type", StringType(), True),
    StructField("cs", LongType(), True),
    StructField("topic", StringType(), True),
    StructField("data", data_schema, True),
])


PRICE_T = DecimalType(18, 8)
VOL_T = DecimalType(22, 4)
PCT_T = DecimalType(10, 6)

log.info("Starting silver processor: topic=%s, bronze=%s, silver=%s", TOPIC, BRONZE_PATH, SILVER_PATH)

source = (spark.readStream
          .format("parquet")
          .schema(bronze_schema)
          .option("maxFilesPerTrigger", 100)
          .load(BRONZE_PATH))

clean = (source
         .withColumn("p", F.from_json(F.col("raw_json"), payload_schema))
         .select(
             F.col("ingestion_ts"),
             F.col("kafka_ts"),
             F.timestamp_millis(F.col("p.ts")).alias("event_time"),
             F.col("p.type").alias("type"),
             F.col("p.cs").alias("cs"),
             F.col("p.data.symbol").alias("symbol"),
             F.col("p.data.lastPrice").cast(PRICE_T).alias("last_price"),
             F.col("p.data.highPrice24h").cast(
                 PRICE_T).alias("high_price_24h"),
             F.col("p.data.lowPrice24h").cast(PRICE_T).alias("low_price_24h"),
             F.col("p.data.prevPrice24h").cast(
                 PRICE_T).alias("prev_price_24h"),
             F.col("p.data.volume24h").cast(VOL_T).alias("volume_24h"),
             F.col("p.data.turnover24h").cast(VOL_T).alias("turnover_24h"),
             F.col("p.data.price24hPcnt").cast(PCT_T).alias("price_24h_pct"),
             F.col("p.data.usdIndexPrice").cast(
                 PRICE_T).alias("usd_index_price"),
         )).dropDuplicates(["event_time", "cs"]).where(~F.isnull("usd_index_price"))\
    .withColumn("year",  F.year("event_time"))\
    .withColumn("month", F.month("event_time"))\
    .withColumn("day",   F.dayofmonth("event_time"))


write = (clean.writeStream
         .format("parquet")
         .option("path", SILVER_PATH)
         .option("checkpointLocation", CHECKPOINT_SILVER_PATH)
         .partitionBy("year", "month", "day")
         .trigger(processingTime="60 seconds")
         .start())

log.info("Stream query started: id=%s", write.id)
write.awaitTermination()

progress = write.lastProgress
if progress:
    log.info(
        "Stream finished: batches=%s, input_rows=%s, output_rows=%s",
        progress.get("batchId"),
        progress.get("numInputRows"),
        progress["sink"].get("numOutputRows") if progress.get("sink") else "n/a",
    )
log.info("Silver processor done")
