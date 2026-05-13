
from utils.spark_session_iceberg import createSpark

try:
    spark.stop()  # type: ignore
except Exception:
    pass

PACKAGES = ",".join([
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1",
])

spark = createSpark()

DDL = """
CREATE TABLE IF NOT EXISTS lake.bronze.tickers_raw (
    raw_json     STRING,
    topic        STRING,
    `partition`  INT,
    `offset`     BIGINT,
    kafka_ts     TIMESTAMP,
    ingestion_ts TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(ingestion_ts))
TBLPROPERTIES (
    'write.target-file-size-bytes'               = '134217728',
    'write.distribution-mode'                    = 'hash',
    'format-version'                             = '2',
    'history.expire.max-snapshot-age-ms'         = '604800000',
    'write.metadata.delete-after-commit.enabled' = 'true'
);

CREATE TABLE IF NOT EXISTS lake.bronze.prices_raw (
    raw_json     STRING,
    topic        STRING,
    `partition`  INT,
    `offset`     BIGINT,
    kafka_ts     TIMESTAMP,
    ingestion_ts TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(ingestion_ts))
TBLPROPERTIES (
    'write.target-file-size-bytes'               = '134217728',
    'write.distribution-mode'                    = 'hash',
    'format-version'                             = '2',
    'history.expire.max-snapshot-age-ms'         = '604800000',
    'write.metadata.delete-after-commit.enabled' = 'true'
);
"""

spark.sql("CREATE NAMESPACE IF NOT EXISTS lake.bronze")
spark.sql("CREATE NAMESPACE IF NOT EXISTS lake.silver")
spark.sql("CREATE NAMESPACE IF NOT EXISTS lake.gold")

for stmt in DDL.strip().split(";"):
    if stmt.strip():
        spark.sql(stmt)
