import logging
from utils.spark_session import create_spark
from utils.bronze_writer import start_bronze_stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bronze_writer")

TOPICS = [
    "crypto.tickers",
    "crypto.ohlcv",
    "crypto.prices",
]

if __name__ == "__main__":
    spark = create_spark()
    queries = [start_bronze_stream(spark, t) for t in TOPICS]

    for q in queries:
        q.awaitTermination()
        progress = q.lastProgress
        if progress:
            log.info(
                "Stream finished: topic=%s, batches=%s, input_rows=%s",
                q.name,
                progress.get("batchId"),
                progress.get("numInputRows"),
            )

    log.info("All bronze streams done")
