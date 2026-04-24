from kafka import KafkaProducer
from dotenv import get_key

import json
import os
import requests
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

producer = KafkaProducer(
    bootstrap_servers=os.environ.get(
        'KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092'),
    api_version=(3, 6, 0),
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8') if k else None,
)

API_KEY = get_key('./env', 'COINGECKO_API_KEY')
URL = 'https://api.coingecko.com/api/v3/coins/markets'
PARAMS = {"vs_currency": "usd"}

while True:
    try:
        resp = requests.get(URL, params=PARAMS, timeout=10)
        resp.raise_for_status()
        for coin in resp.json():
            producer.send("crypto.prices", key=coin["symbol"], value=coin)
        else:
            logging.info("Sent coin data to producer")
    except Exception as e:
        logging.error(f"Error: {e}")
    time.sleep(60)
