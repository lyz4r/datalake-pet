# ACHTUNG ВОНО НЕ РОБИТЬ

import datetime
import json
from datetime import timedelta

from airflow.decorators import dag
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include.coin_universe import COIN_IDS

TOPIC = "crypto.prices"
SILVER_PATH = f"s3a://crypto-lake/silver/{TOPIC}"
GOLD_PATH = f"s3a://crypto-lake/gold/{TOPIC}"


@dag(
    dag_id="gold_prices_hourly",
    start_date=datetime.datetime(2026, 5, 6),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["gold", "prices"],
)
def gold_prices_hourly():
    SparkSubmitOperator(
        task_id="aggregate_prices",
        conn_id="spark_default",
        application="/opt/jobs/gold_prices_aggregator.py",
        application_args=[
            "--bucket_from", "{{ (data_interval_start - macros.timedelta(hours=1)).isoformat() }}",
            "--bucket_to",   "{{ (data_interval_end   - macros.timedelta(hours=1)).isoformat() }}",
            "--granularity", "hour",
            "--coin_ids",    json.dumps(COIN_IDS),
            "--silver_path", SILVER_PATH,
            "--gold_path",   GOLD_PATH,
        ],
    )


gold_prices_hourly()
