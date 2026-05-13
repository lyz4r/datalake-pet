from utils.spark_iceberg_session import create_session
import pyspark.sql.functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, ArrayType,
    DecimalType, FloatType, IntegerType
)

spark = create_session()

TOPIC = "prices"
CHECKPOINT_BRONZE_PATH = f"s3a://spark-checkpoints/lakehouse/bronze/{TOPIC}_raw"
CHECKPOINT_SILVER_PATH = f"s3a://spark-checkpoints/lakehouse/silver/{TOPIC}"

# схема вложенной структуры полезной нагрузки
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


source = (spark.readStream
          .format("iceberg")
          .load(f"lake.bronze.{TOPIC}_raw"))

PRICE_T, CAP_T, VOL_T, SUPPLY_T = (
    DecimalType(28, 8), DecimalType(28, 2),
    DecimalType(28, 2), DecimalType(28, 8),
)
PCT_T, RANK_T = FloatType(), IntegerType()

clean = (source
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
         .format("iceberg")
         .option("checkpointLocation", CHECKPOINT_SILVER_PATH)
         .option("fanout-enabled", "true")
         .trigger(availableNow=True)
         .outputMode("append")
         .toTable(f"lake.silver.{TOPIC}"))

write.awaitTermination()
