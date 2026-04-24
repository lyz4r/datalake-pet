#!/bin/bash
set -e

BROKER="kafka:9092"

create_topic() {
    local topic=$1
    local partitions=$2
    local retention_ms=$3

    kafka-topics --bootstrap-server $BROKER \
        --create --if-not-exists \
        --topic $topic \
        --partitions $partitions \
        --replication-factor 1 \
        --config retention.ms=$retention_ms
    echo "Topic $topic ready"
}

# retention в ms: 1 день = 86400000
create_topic "crypto.prices"    6 604800000     # 7 дней
create_topic "crypto.sentiment" 1 7776000000    # 90 дней
create_topic "crypto.ohlcv"     3 2592000000    # 30 дней
create_topic "crypto.global"    1 2592000000    # 30 дней

kafka-topics --bootstrap-server $BROKER --list