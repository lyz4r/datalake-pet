# TODO: все же надо переделать на батч
from utils.kafka_client import KafkaClient

import requests
import logging
import time
import schedule
import json

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REQUEST_DELAY = 2.0
RETRY_DELAY = 60.0


def get_coins_list(url: str) -> list:
    resp = requests.get(url)
    resp.raise_for_status()
    coin_list = [item["id"] for item in resp.json()]
    log.info(f"Fetched coin list with {len(coin_list)} coins")
    return coin_list


def get_ohlcv(url: str, params: dict, coin_list: list[str]):
    for coin_id in coin_list:
        url_coin = f"{url}/{coin_id}/ohlc"
        try:
            resp = requests.get(url_coin, params=params)
            if resp.status_code == 429:
                log.warning(
                    f"Rate limited on {coin_id}, retrying after {RETRY_DELAY}s")
                time.sleep(RETRY_DELAY)
                resp = requests.get(url_coin, params=params)
            resp.raise_for_status()
            payload = {
                "coin_id": coin_id,
                "vs_currency": "usd",
                "days": 90,
                "fetched_at": int(time.time() * 1000),
                "ohlc": resp.json(),
            }
            yield json.dumps(payload)
        except Exception as e:
            log.error(f"Failed to fetch OHLCV for {coin_id}: {e}")
        time.sleep(REQUEST_DELAY)


def generator_to_kafka(url_coin_list: str, url_ohlcv: str, params_ohlcv: dict, topic: str):
    with KafkaClient() as producer:
        coin_list = get_coins_list(url_coin_list)
        for ohlcv in get_ohlcv(url_ohlcv, params_ohlcv, coin_list):
            try:
                producer.send(topic, ohlcv)
            except Exception as e:
                log.error(f"Failed to send OHLCV data to Kafka: {e}")


if __name__ == "__main__":
    URL_OHLCV = "https://api.coingecko.com/api/v3/coins/"
    URL_COIN_LIST = "https://api.coingecko.com/api/v3/coins/list"
    PARAMS_OHLCV = {
        "vs_currency": "usd",
        "days": 90
    }
    TOPIC = "crypto.ohlcv"

    def job():
        generator_to_kafka(URL_COIN_LIST, URL_OHLCV, PARAMS_OHLCV, TOPIC)

    job()
    schedule.every().day.at("00:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)
