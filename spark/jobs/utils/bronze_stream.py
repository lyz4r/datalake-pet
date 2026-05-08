import logging
import pyspark.sql.functions as F

log = logging.getLogger("bronze_writer")


def startBronzeStream(spark, topic):
    checkpoint_path = f"s3a://spark-checkpoints/bronze/{topic}"
    bronze_path = f"s3a://crypto-lake/bronze/{topic}"

    source = (spark.readStream
              .format("kafka")
              .option("kafka.bootstrap.servers", "kafka:9092")
              .option("subscribe", topic)
              .option("startingOffsets", "earliest")
              .load())

    parsed = (source
              .selectExpr("CAST(value AS STRING) as raw_json", "topic", "partition", "offset", "timestamp as kafka_ts")
              .withColumn("ingestion_ts", F.current_timestamp())
              .withColumn("year",  F.year("kafka_ts"))
              .withColumn("month", F.month("kafka_ts"))
              .withColumn("day",   F.dayofmonth("kafka_ts"))
              .withColumn("hour",  F.hour("kafka_ts")))

    query = (parsed.writeStream
             .format("parquet")
             .option("path", bronze_path)
             .option("checkpointLocation", checkpoint_path)
             .partitionBy("year", "month", "day", "hour")
             .trigger(availableNow=True)
             .outputMode("append")
             .start())

    log.info("Bronze stream started: topic=%s, id=%s", topic, query.id)
    return query
