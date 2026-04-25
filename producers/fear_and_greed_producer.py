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
            kafka_client.fetch_and_send(URL, PARAMS, topic="crypto.sentiment", key="data")
        except Exception as e:
            logger.error(f"Error in Kafka Fear and greed producer: {e}")


if __name__ == "__main__":
    fetch_and_produce()
            
