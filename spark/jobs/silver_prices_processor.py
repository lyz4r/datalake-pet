import logging
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, ArrayType,
    DecimalType, FloatType, IntegerType
)
from utils.spark_session import createSpark


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("silver_prices_processor")

PRICE_T, CAP_T, VOL_T, SUPPLY_T = (
    DecimalType(28, 8), DecimalType(28, 2),
    DecimalType(28, 2), DecimalType(28, 8),
)
PCT_T, RANK_T = FloatType(), IntegerType()

TOPIC = "crypto.prices"
CHECKPOINT_BRONZE_PATH = f"s3a://spark-checkpoints/bronze/{TOPIC}"
CHECKPOINT_SILVER_PATH = f"s3a://spark-checkpoints/silver/{TOPIC}"
BRONZE_PATH = f"s3a://crypto-lake/bronze/{TOPIC}"
SILVER_PATH = f"s3a://crypto-lake/silver/{TOPIC}"


coin_schema = StructType([
    StructField("id", StringType()),
    StructField("symbol", StringType()),
    StructField("name", StringType()),
    StructField("image", StringType()),
    StructField("current_price", StringType()),
    StructField("market_cap", StringType()),
    StructField("market_cap_rank", StringType()),
    StructField("fully_diluted_valuation", StringType()),
    StructField("total_volume", StringType()),
    StructField("high_24h", StringType()),
    StructField("low_24h", StringType()),
    StructField("price_change_24h", StringType()),
    StructField("price_change_percentage_24h", StringType()),
    StructField("market_cap_change_24h", StringType()),
    StructField("market_cap_change_percentage_24h", StringType()),
    StructField("circulating_supply", StringType()),
    StructField("total_supply", StringType()),
    StructField("max_supply", StringType()),
    StructField("ath", StringType()),
    StructField("ath_change_percentage", StringType()),
    StructField("ath_date", StringType()),
    StructField("atl", StringType()),
    StructField("atl_change_percentage", StringType()),
    StructField("atl_date", StringType()),
    StructField("last_updated", StringType()),
])
payload_schema = ArrayType(coin_schema)

spark = createSpark()

bronze = (spark.readStream
          .schema(spark.read.parquet(BRONZE_PATH).schema)
          .parquet(BRONZE_PATH))

clean = (bronze
         .withColumn("arr", F.from_json("raw_json", payload_schema))
         .withColumn("p", F.explode("arr"))
         .select(
             F.col("ingestion_ts"),
             F.col("kafka_ts"),
             F.to_timestamp("p.last_updated").alias("event_time"),
             F.col("p.id").alias("coin_id"),
             F.upper("p.symbol").alias("symbol"),
             F.col("p.name").alias("name"),
             F.col("p.image").alias("image_url"),
             F.col("p.current_price").cast(PRICE_T).alias("current_price"),
             F.col("p.market_cap").cast(CAP_T).alias("market_cap"),
             F.col("p.market_cap_rank").cast(RANK_T).alias("market_cap_rank"),
             F.col("p.fully_diluted_valuation").cast(
                 CAP_T).alias("fully_diluted_valuation"),
             F.col("p.total_volume").cast(VOL_T).alias("total_volume"),
             F.col("p.high_24h").cast(PRICE_T).alias("high_24h"),
             F.col("p.low_24h").cast(PRICE_T).alias("low_24h"),
             F.col("p.price_change_24h").cast(
                 PRICE_T).alias("price_change_24h"),
             F.col("p.price_change_percentage_24h").cast(
                 PCT_T).alias("price_change_pct_24h"),
             F.col("p.market_cap_change_24h").cast(
                 CAP_T).alias("market_cap_change_24h"),
             F.col("p.market_cap_change_percentage_24h").cast(
                 PCT_T).alias("market_cap_change_pct_24h"),
             F.col("p.circulating_supply").cast(
                 SUPPLY_T).alias("circulating_supply"),
             F.col("p.total_supply").cast(SUPPLY_T).alias("total_supply"),
             F.col("p.max_supply").cast(SUPPLY_T).alias("max_supply"),
             F.col("p.ath").cast(PRICE_T).alias("ath"),
             F.col("p.ath_change_percentage").cast(
                 PCT_T).alias("ath_change_pct"),
             F.to_timestamp("p.ath_date").alias("ath_date"),
             F.col("p.atl").cast(PRICE_T).alias("atl"),
             F.col("p.atl_change_percentage").cast(
                 PCT_T).alias("atl_change_pct"),
             F.to_timestamp("p.atl_date").alias("atl_date"),
         )
         .where(F.col("current_price").isNotNull() & (F.col("current_price") > 0))
         .withWatermark("event_time", "10 minutes")
         .dropDuplicates(["coin_id", "event_time"])
         .withColumn("year",  F.year("event_time"))
         .withColumn("month", F.month("event_time"))
         .withColumn("day",   F.dayofmonth("event_time"))
         )

write = (clean.writeStream
         .format("parquet")
         .option("path", SILVER_PATH)
         .option("checkpointLocation", CHECKPOINT_SILVER_PATH)
         .partitionBy("coin_id", "year", "month", "day")
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
        progress["sink"].get("numOutputRows") if progress.get(
            "sink") else "n/a",
    )
log.info("Silver processor done")
