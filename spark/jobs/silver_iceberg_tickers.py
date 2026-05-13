from utils.spark_iceberg_session import create_session
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, DecimalType, LongType, TimestampType, DoubleType

spark = create_session()

TOPIC = "tickers"
CHECKPOINT_BRONZE_PATH = f"s3a://spark-checkpoints/lakehouse/bronze/{TOPIC}_raw"
CHECKPOINT_SILVER_PATH = f"s3a://spark-checkpoints/lakehouse/silver/{TOPIC}"

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


PRICE_T = DecimalType(28, 12)
VOL_T = DecimalType(38, 8)
PCT_T = DecimalType(10, 6)

source = (spark.readStream
          .format("iceberg")
          .load(f"lake.bronze.{TOPIC}_raw"))

clean = (source
         .withColumn("p", F.from_json(F.col("raw_json"), payload_schema))
         .select(
             F.col("p.data.symbol").alias("symbol"),
             F.col("p.type").alias("event_type"),
             F.col("p.cs").alias("cross_seq"),
             F.timestamp_millis(F.col("p.ts")).alias("event_ts"),
             F.col("ingestion_ts"),
             F.col("p.data.lastPrice").cast(PRICE_T).alias("last_price"),
             F.col("p.data.highPrice24h").cast(
                 PRICE_T).alias("high_price_24h"),
             F.col("p.data.lowPrice24h").cast(PRICE_T).alias("low_price_24h"),
             F.col("p.data.prevPrice24h").cast(
                 PRICE_T).alias("prev_price_24h"),
             F.col("p.data.usdIndexPrice").cast(
                 PRICE_T).alias("usd_index_price"),
             F.col("p.data.volume24h").cast(VOL_T).alias("volume_24h"),
             F.col("p.data.turnover24h").cast(VOL_T).alias("turnover_24h"),
             F.col("p.data.price24hPcnt").cast(
                 DoubleType()).alias("price_24h_pcnt"),
         )
         .where(
             F.col("symbol").isNotNull() &
             F.col("event_type").isNotNull() &
             F.col("event_ts").isNotNull() &
             F.col("ingestion_ts").isNotNull() &
             F.col("usd_index_price").isNotNull()
         )
         .withWatermark("event_ts", "10 minutes")
         .dropDuplicates(["event_ts", "cross_seq"])
         )


write = (clean.writeStream
         .format("iceberg")
         .option("checkpointLocation", CHECKPOINT_SILVER_PATH)
         .option("fanout-enabled", "true")
         .trigger(availableNow=True)
         .outputMode("append")
         .toTable(f"lake.silver.{TOPIC}"))

write.awaitTermination()
