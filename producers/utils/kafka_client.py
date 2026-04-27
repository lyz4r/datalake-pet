from kafka import KafkaProducer


import json
import requests
import os


class KafkaClient:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            acks="all",
            retries=5,
        )

    def fetch(self, URL: str, params: dict) -> requests.Response:
        resp = requests.get(URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp

    def send(self, iterative: bool, resp: requests.Response, topic: str, key: str):
        resp_json = resp.json()
        if iterative:
            for value in resp_json:
                self.producer.send(topic, key=value[key], value=value)
        else:
            self.producer.send(topic, key=resp_json[key], value=resp_json)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.producer.flush(timeout=10)
        self.producer.close()
