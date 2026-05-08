import argparse
import json
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket_from", required=True)
    parser.add_argument("--bucket_to", required=True)
    parser.add_argument("--granularity", default="hour")
    parser.add_argument("--coin_ids", required=True)
    parser.add_argument("--silver_path", required=True)
    parser.add_argument("--gold_path", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    coin_ids = json.loads(args.coin_ids)

    spark = SparkSession.builder.appName("gold_prices_aggregator").getOrCreate()
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    silver = (
        spark.read.parquet(args.silver_path)
        .filter(F.col("event_time") >= F.lit(args.bucket_from).cast("timestamp"))
        .filter(F.col("event_time") < F.lit(args.bucket_to).cast("timestamp"))
        .filter(F.col("coin_id").isin(coin_ids))
    )

    aggregated = (
        silver
        .withColumn("bucket_start", F.date_trunc(args.granularity, "event_time"))
        .groupBy("coin_id", "bucket_start")
        .agg(
            F.max("current_price").alias("max_price"),
            F.max(F.struct("event_time", "market_cap")).alias("_last"),
        )
        .select(
            "coin_id", "bucket_start", "max_price",
            F.col("_last.market_cap").alias("market_cap"),
        )
        .withColumn("year",  F.year("bucket_start"))
        .withColumn("month", F.month("bucket_start"))
        .withColumn("day",   F.dayofmonth("bucket_start"))
    )

    (
        aggregated.write
        .mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(args.gold_path)
    )

    spark.stop()


if __name__ == "__main__":
    main()
