from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, year, month, dayofmonth, hour


def main():
    spark = SparkSession.builder \
        .appName("bronze_writer_prices") \
        .getOrCreate()

    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "crypto.prices") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    bronze = df.select(
        col("value").cast("string").alias("kafka_value_raw"),
        col("key").cast("string").alias("kafka_key"),
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_timestamp"),
        current_timestamp().alias("ingestion_ts"),
    ).withColumn("year", year("ingestion_ts")) \
     .withColumn("month", month("ingestion_ts")) \
     .withColumn("day", dayofmonth("ingestion_ts")) \
     .withColumn("hour", hour("ingestion_ts"))

    query = bronze.writeStream \
        .format("parquet") \
        .option("path", "s3a://bucket/bronze/prices/") \
        .option("checkpointLocation", "s3a://bucket/checkpoints/bronze_prices/") \
        .partitionBy("year", "month", "day", "hour") \
        .outputMode("append") \
        .trigger(processingTime="30 seconds") \
        .start()

    query.awaitTermination()


if __name__ == "__main__":
    main()
