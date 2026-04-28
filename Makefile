.PHONY: help up down restart logs ps clean nuke ch-cli kafka-topics check-env

help:
	@echo "CryptoFlow MVP commands"
	@echo "  make check-env   - validate .env exists and required secrets are set"
	@echo "  make up          - start all services in background"
	@echo "  make down        - stop all services (keep volumes)"
	@echo "  make restart     - restart all services"
	@echo "  make logs S=name - tail logs of service (e.g. make logs S=spark-master)"
	@echo "  make ps          - list running services with health"
	@echo "  make clean       - down + remove containers (keep volumes)"
	@echo "  make nuke        - down + remove containers AND volumes (data loss!)"
	@echo "  make ch-cli      - open ClickHouse client"
	@echo "  make kafka-topics - list Kafka topics"

check-env:
	@test -f .env || (echo "ERROR: .env not found. Copy .env.example to .env and fill secrets." && exit 1)
	@grep -q "AIRFLOW_FERNET_KEY=." .env || (echo "ERROR: AIRFLOW_FERNET_KEY is empty. Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'" && exit 1)
	@echo "OK"

up: check-env
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f $(S)

ps:
	docker compose ps

clean:
	docker compose down --remove-orphans

nuke:
	docker compose down -v --remove-orphans

ch-cli:
	docker compose exec clickhouse clickhouse-client --password $$(grep CLICKHOUSE_PASSWORD .env | cut -d= -f2)

kafka-topics:
	docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list

kafka-consume:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic $(T) --from-beginning --max-messages 10
