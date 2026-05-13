from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator

default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
}


with DAG(
    dag_id="gold_prices",
    description="DAG для создания витрины данных со статистикой по различных монет из Coingecko API",
    start_date=datetime(2026, 5, 1),
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

    with TaskGroup("dim_coin") as dim_coin:
        create_table = ClickHouseOperator(
            task_id="create_dim_coin",
            sql="create_dim_coin.sql",
            clickhouse_conn_id="clickhouse_default"
        )
        insert_data = ClickHouseOperator(
            task_id="insert_into_dim_coin",
            sql="insert_into_dim_coin.sql",
            clickhouse_conn_id="clickhouse_default"
        )
        create_table >> insert_data
    with TaskGroup("fact_prices") as fact_prices:
        create_table = ClickHouseOperator(
            task_id="create_fact_prices",
            sql="create_fact_prices.sql",
            clickhouse_conn_id="clickhouse_default"
        )
        insert_data = ClickHouseOperator(
            task_id="insert_into_fact_prices",
            sql="insert_into_fact_prices.sql",
            clickhouse_conn_id="clickhouse_default"
        )
        create_table >> insert_data

    # backup_data = ClickHouseOperator(
    #     task_id="backup_gold",
    #     sql="backup_gold.sql",
    #     clickhouse_conn_id="clickhouse_default"
    # )

    dim_coin >> fact_prices  # >> backup_data
