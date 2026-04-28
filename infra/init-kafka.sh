#!/bin/sh
set -e

BOOTSTRAP="kafka:9092"
KAFKA_BIN="/opt/kafka/bin"

echo "[kafka-init] Waiting for Kafka..."
until $KAFKA_BIN/kafka-broker-api-versions.sh --bootstrap-server $BOOTSTRAP >/dev/null 2>&1; do
  sleep 2
done

create_topic() {
  TOPIC=$1
  PARTITIONS=$2
  RETENTION_MS=${3:-604800000}  # default 7 days
  echo "[kafka-init] Creating topic $TOPIC (partitions=$PARTITIONS, retention=${RETENTION_MS}ms)"
  $KAFKA_BIN/kafka-topics.sh --bootstrap-server $BOOTSTRAP \
    --create --if-not-exists \
    --topic $TOPIC \
    --partitions $PARTITIONS \
    --replication-factor 1 \
    --config retention.ms=$RETENTION_MS \
    --config compression.type=lz4
}

create_topic crypto.tickers   6   259200000   # 3 days
create_topic crypto.prices    3   604800000   # 7 days
create_topic crypto.trades    6   86400000    # 1 day
create_topic crypto.ohlcv     3   2592000000  # 30 days
create_topic crypto.sentiment 1   7776000000  # 90 days

echo "[kafka-init] Topics:"
$KAFKA_BIN/kafka-topics.sh --bootstrap-server $BOOTSTRAP --list

echo "[kafka-init] Done."
