from datetime import datetime, timedelta

from airflow import DAG
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator

with DAG(
    dag_id="gold_tickers",
    description="DAG для создания витрины данных со статистикой по Bitcoin из Bybit WebSocket",
    start_date=datetime(2026, 4, 28),
    catchup=True,
    schedule="@daily",
    default_args={
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
        'retry_exponential_backoff': True,
        'max_retry_delay': timedelta(hours=1),
    },
    template_searchpath="/opt/airflow/include/sql"
) as dag:
    create_mart = ClickHouseOperator(
        task_id="create_fact_tickers",
        sql="create_fact_tickers.sql",
        clickhouse_conn_id="clickhouse_default"
    )
    insert_data = ClickHouseOperator(
        task_id="insert_into_fact_tickers",
        sql="insert_into_fact_tickers.sql",
        retries=3,
        retry_delay=timedelta(minutes=5),
        clickhouse_conn_id="clickhouse_default"
    )
    # backup_data = ClickHouseOperator(
    #     task_id="backup_gold",
    #     sql="backup_gold.sql",
    #     retries=3,
    #     retry_delay=timedelta(minutes=5),
    #     clickhouse_conn_id="clickhouse_default"
    # )
    create_mart >> insert_data  # >> backup_data
