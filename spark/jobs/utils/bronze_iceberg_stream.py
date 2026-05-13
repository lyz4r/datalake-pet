import logging
import pyspark.sql.functions as F

log = logging.getLogger("bronze_writer")


def start_bronze_stream(spark, topic):
    CHECKPOINT_PATH = f"s3a://spark-checkpoints/lakehouse/bronze/{topic}_raw"

    source = (spark.readStream.format("kafka")
              .option("kafka.bootstrap.servers", "kafka:9092")
              .option("subscribe", f"crypto.{topic}")
              .option("startingOffsets", "earliest")
              .load()
              )

    parsed = (source.selectExpr("CAST(value AS STRING) as raw_json", "topic", "partition", "offset", "timestamp as kafka_ts")
              .withColumn("ingestion_ts", F.current_timestamp()))

    query = (parsed.writeStream.format("iceberg")
             .option("checkpointLocation", CHECKPOINT_PATH)
             .option("fanout-enabled", "true")
             .trigger(availableNow=True)
             .outputMode("append")
             .toTable(f"lake.bronze.{topic}_raw"))
    log.info("Bronze stream to Iceberg started: topic=%s, id=%s", topic, query.id)
    return query
