from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from fear_and_greed_producer import fetch_and_produce


with DAG(
    dag_id="batch_producers",
    description="DAG для пакетной загрузки" \
    " криптовалютых данных из разных источников." \
    " На текущий момент поддерживаются: Fear And Greed Index.",
    schedule="@daily",
    start_date=datetime(2026, 4, 1),
    catchup=False,
    tags=["batch", "producers"],
) as dag:
    fng_task = PythonOperator(
        task_id="fetch_fear_greed",
        python_callable=fetch_and_produce,
    )

    fng_task