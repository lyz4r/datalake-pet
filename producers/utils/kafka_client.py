from kafka import KafkaProducer

import json
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

    def send(self, topic, value=None, key=None):
        self.producer.send(topic, value=value, key=key)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.producer.flush(timeout=10)
        self.producer.close()
