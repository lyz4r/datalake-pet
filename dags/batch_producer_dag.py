from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import requests
import logging

log = logging.getLogger(__name__)

URL = "https://api.alternative.me/fng/"
PARAMS = {"limit": 30}


def fng_producer():
    try:
        resp = requests.get(url=URL, params=PARAMS, timeout=10)
        log.info(f"Fetched fng index data: {resp.json()}")
    except Exception as e:
        log.error(f"Could not fetch fng index data: {e}")

    return


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    'batch_producer_dag',
    default_args=default_args,
    description="""DAG для батчевого сбора информации
    о состоянии индекса страха и скупости
    рынка криптовалют по API""",
    schedule_interval="@daily",
    start_date=datetime(2026, 4, 20, 4, 20),
    catchup=True,
    tags=['crypto'],
) as dag:

    producer = PythonOperator(
        task_id="fng_producer",
        python_callable=fng_producer
    )

    producer
