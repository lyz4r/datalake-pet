from datetime import datetime

from airflow import DAG
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator

with DAG(
    dag_id="gold_tickers",
    description="DAG для создания витрины данных со статистикой по Bitcoin из Bybit WebSocket",
    start_date=datetime(2026, 5, 28),
    catchup=True,
    schedule="@daily",
    template_searchpath="/opt/airflow/include/sql"
) as dag:
    create_mart = ClickHouseOperator(
        task_id="create_fact_tickers",
        sql="create_mart_tickers.sql",
        clickhouse_conn_id="clickhouse_default"
    )
    insert_data = ClickHouseOperator(
        task_id="insert_into_fact_tickers",
        sql="insert_into_mart_tickers.sql",
        clickhouse_conn_id="clickhouse_default"
    )
    create_mart >> insert_data
