from utils.kafka_client import KafkaClient

import os
import time
import logging


logger = logging.getLogger(__name__)

URL = "https://api.alternative.me/fng/"
PARAMS = {"limit": 1}


def fetch_and_produce():
    with KafkaClient() as kafka_client:
        try:
            resp = kafka_client.fetch(
                URL, PARAMS)
            logger.info("Fetched FNG data")
            kafka_client.send(iterative=False, resp=resp,
                              topic="crypto.sentiment", key="data")
            logger.info(f"Sent FNG data to Kafka {resp}")
        except Exception as e:
            logger.error(f"Error in Kafka Fear and greed producer: {e}")


if __name__ == "__main__":
    fetch_and_produce()
