from utils.kafka_client import KafkaClient

import os
import time
import logging

os.makedirs("/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/logs/coingecko_producer.log"),
        logging.StreamHandler(),
    ],
)


URL = 'https://api.coingecko.com/api/v3/coins/markets'
PARAMS = {"vs_currency": "usd"}


def main():
    with KafkaClient() as kafka_client:
        while True:
            try:
                resp = kafka_client.fetch(
                    URL, PARAMS)
                kafka_client.send(iterative=True, resp=resp,
                                  topic="crypto.prices", key="symbol")
            except Exception as e:
                logging.error(f"Error in Kafka Coingecko producer: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
