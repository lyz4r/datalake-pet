# Гайд по развёртыванию CryptoFlow

## Требования

- Docker 27.5+ и Docker Compose v2
- **16 GB RAM** минимум (стек тяжёлый: Spark + Airflow + ClickHouse + Kafka). 8 GB хватит, если выключить spark-worker и Airflow temporarily.
- 20 GB свободного места на диске
- Linux/macOS (Windows — через WSL2)

## Версии (актуальные на апрель 2026)

| Компонент    | Версия     | Image                                    |
|--------------|-----------|------------------------------------------|
| Kafka        | 4.1.2     | `apache/kafka:4.1.2`                     |
| MinIO        | latest    | `minio/minio:latest`                     |
| ClickHouse   | 25.8 LTS  | `clickhouse/clickhouse-server:25.8`      |
| Spark        | 3.5.5     | custom (`apache/spark:3.5.5-python3` + JARs) |
| Airflow      | 3.2.1     | custom (`apache/airflow:3.2.1-python3.12`)   |
| Superset     | 5.0.0     | custom (`apache/superset:5.0.0` + driver)    |
| Postgres     | 17        | `postgres:17-alpine`                     |

**Почему Spark 3.5.5, а не 4.0/4.1:** связка Iceberg + Spark 4.x всё ещё имеет известные несовместимости (issue [#15238](https://github.com/apache/iceberg/issues/15238) и др.). 3.5.5 — последняя стабильная для Iceberg 1.10.x.

**Почему Airflow 3.2.1 а не 2.x:** 2.x EOL ожидается, 3.2.1 уже стабильна (вышла 22 апреля 2026). Главное отличие в compose: вместо `webserver` теперь `api-server`, и `dag-processor` обязательный отдельный сервис.

## Структура проекта

```
crypto-flow/
├── docker-compose.yml
├── .env.example         # → скопируй в .env, заполни секреты
├── Makefile             # удобные команды
├── PLAN.md              # план разработки по фазам
├── DEPLOYMENT.md        # этот файл
├── airflow/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── dags/            # сюда кладёшь свои DAG'и
├── spark/
│   ├── Dockerfile       # с jars: hadoop-aws, kafka, iceberg, ch-jdbc
│   └── jobs/            # сюда кладёшь pyspark скрипты
├── producers/
│   ├── Dockerfile
│   └── requirements.txt
├── superset/
│   └── Dockerfile       # с clickhouse-connect
├── clickhouse/
│   └── init/
│       └── 01_schema.sql  # автоматически применяется при первом запуске
└── infra/
    ├── init-kafka.sh    # создаёт топики
    ├── init-minio.sh    # создаёт бакеты
    └── init-postgres.sh # создаёт базу superset
```

---

## Запуск с нуля

### 1. Клонируй и подготовь .env

```bash
git clone <repo> crypto-flow && cd crypto-flow
cp .env.example .env
```

Сгенерируй `AIRFLOW_FERNET_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Сгенерируй секреты для API/JWT/Superset:
```bash
openssl rand -hex 32   # подставь в AIRFLOW_API_SECRET, AIRFLOW_JWT_SECRET, SUPERSET_SECRET_KEY
```

На Linux ещё:
```bash
echo "AIRFLOW_UID=$(id -u)" >> .env
```

### 2. Подними стек

```bash
make up
# или: docker compose up -d --build
```

Первый запуск ≈5–10 мин (build образов + скачивание JAR-ов ≈600 MB).

### 3. Проверь, что всё живо

```bash
make ps
```

Все сервисы должны быть `healthy` или `running` (init-контейнеры — `exited (0)`).

### 4. UI на хост-машине

| Сервис      | URL                    | Логин/пароль                     |
|-------------|------------------------|----------------------------------|
| Airflow     | http://localhost:8080  | admin / admin (из .env)         |
| Superset    | http://localhost:8088  | admin / admin (из .env)         |
| MinIO       | http://localhost:9001  | minioadmin / minioadmin         |
| Spark UI    | http://localhost:8081  | —                                |
| ClickHouse  | http://localhost:8123  | default / clickhouse (HTTP API) |
| Kafka       | localhost:29092        | (PLAINTEXT, из хоста)            |

### 5. Smoke-тесты

```bash
# Kafka — список топиков
make kafka-topics
# должно показать crypto.tickers, crypto.prices, crypto.ohlcv, ...

# ClickHouse — список таблиц
docker compose exec clickhouse clickhouse-client \
  --password "$(grep CLICKHOUSE_PASSWORD .env | cut -d= -f2)" \
  -q "SHOW TABLES FROM crypto"

# MinIO — список бакетов (через UI или mc)
docker compose exec -T minio mc alias set local http://minio:9000 minioadmin minioadmin
docker compose exec -T minio mc ls local
```

---

## Настройка Superset → ClickHouse (после первого старта)

1. Залогинься в http://localhost:8088
2. Settings → Database Connections → `+ Database`
3. Выбери **ClickHouse Connect** в списке
4. SQLAlchemy URI:
   ```
   clickhousedb://default:clickhouse@clickhouse:8123/crypto
   ```
   (пароль возьми из `.env`)
5. Test Connection → Connect

После этого создавай Dataset на `crypto.raw_tickers` (когда там появятся данные после Phase 3).

---

## Типовые проблемы

### `airflow-init` падает с ошибкой про FERNET_KEY
Не сгенерировал ключ. См. шаг 1.

### `spark-bronze-streamer` не может подключиться к S3
Проверь, что `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` пробрасываются в spark-контейнер как `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

### ClickHouse не видит сообщений из Kafka
Это нормально, пока продьюсер не запущен. Проверить:
```sql
SELECT * FROM system.kafka_consumers FORMAT Vertical;
```
Если ошибка типа `Cannot parse JSON` — проверь, что схема в `kafka_tickers` совпадает с тем, что пишет продьюсер.

### Spark worker не присоединяется к master
Чаще всего — конфликт по сети или master не успел подняться. `docker compose restart spark-worker`.

### Airflow UI показывает «No DAGs»
В Airflow 3.x DAG-файлы парсит **отдельный** контейнер `airflow-dag-processor`. Проверь его логи: `make logs S=airflow-dag-processor`. Без этого контейнера DAG'и не появятся, даже если файлы лежат в `/opt/airflow/dags/`.

### Не хватает RAM
Закомментируй `spark-worker` (Phase 0–4 без него работают), уменьши Airflow до одного `api-server + scheduler + dag-processor` без `triggerer`. Можно сэкономить ≈3–4 GB.

---

## Полный сброс (если что-то пошло не так)

```bash
make nuke   # удаляет ВСЕ данные (volumes)
make up
```

---

## Дальнейшие шаги

См. `PLAN.md` — порядок реализации MVP по фазам. Сначала фаза 0 (этот гайд), затем фаза 1 (продьюсер) и далее.
