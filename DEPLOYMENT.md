# Гайд по развёртыванию

1. Поднимаем топики в Kafka
`docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list`

2. Запускаем `notebooks\migrations\create_silver_tables.ipynb` и `notebooks\migrations\create_silver_tables.ipynb`
Проверяес в Minio UI создались Iceberg-таблицы в бакете iceberg-lakehouse

3. Запускаем Superset:
  В Database Connection ставим 172.17.0.1:8123 (localhost не подключится)

