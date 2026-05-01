import requests
import json
import logging
import time

from utils.kafka_client import KafkaClient

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def get_coingecko(url: str, params: dict):
    resp = requests.get(url, params)
    resp.raise_for_status()
    msg = resp.json()
    log.info(f"Recieved Coingecko data for {len(msg)} coins")
    return msg


def poll_coingecko(url: str, params: dict):
    while True:
        try:
            yield get_coingecko(url, params)
            time.sleep(60)
        except Exception as e:
            log.error(f"Could not fetch Coingecko data: {e}. Retrying in 5s.")
            time.sleep(5)


def generator_to_kafka(topic: str, url: str, params: dict):
    with KafkaClient() as producer:
        for msg in poll_coingecko(url, params):
            try:
                producer.send(topic, msg)
                log.info(f"Sent Coingecko data to Kafka {topic}")
            except Exception as e:
                log.error(f"Cound not send Coingecko data to Kafka: {e}")


if __name__ == "__main__":
    TOPIC = "crypto.prices"
    URL = 'https://api.coingecko.com/api/v3/coins/markets'
    PARAMS = {"vs_currency": "usd"}
    generator_to_kafka(TOPIC, URL, PARAMS)
