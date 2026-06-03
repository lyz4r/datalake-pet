import json
import os

from kafka import KafkaConsumer


class KafkaConsumerClient:
    def __init__(self, topic: str, group_id: str):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            group_id=group_id,
            auto_offset_reset="latest",
            value_deserializer=lambda b: json.loads(b.decode()),
        )

    def __iter__(self):
        for msg in self.consumer:
            yield msg.value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.consumer.close()
