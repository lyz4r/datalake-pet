# CryptoFlow — план разработки

**Принцип:** каждая фаза заканчивается рабочим end-to-end куском. Не идём дальше, пока предыдущая не работает.

**Стек:**
Kafka 4.1 (KRaft) → Spark 3.5.5 Structured Streaming → MinIO (Parquet/Iceberg) + ClickHouse 25.8 → Superset 5.0. Оркестрация — Airflow 3.2.1.

---

## MVP — ВЫПОЛНЕНО ✅

| Фаза | Что сделано |
|------|-------------|
| 0 — Инфраструктура | `docker compose up -d` поднимает весь стек. Init-контейнеры создают бакеты MinIO и топики Kafka. |
| 1 — Продьюсер Bybit | `bybit_ws_producer.py` — WebSocket-клиент, топик `crypto.tickers`, reconnect с backoff. |
| 2 — Bronze слой | `bronze_writer.py` — Spark Streaming Kafka → MinIO Parquet, партиции по дате/часу, checkpoint в S3. |
| 3 — Hot path ClickHouse | Kafka Engine + Materialized View → `raw_tickers` (ReplacingMergeTree). Лаг — секунды. |
| 4 — Superset дашборд | Подключён к ClickHouse, dataset на `raw_tickers`, базовые чарты. |
| 5 — Второй продьюсер + Airflow | `coingecko_polling_producer.py` — REST polling, топик `crypto.prices`. DAG-оркестрация. |
| 6 — Silver слой | `silver_tickers_processor.py`, `silver_prices_processor.py` — дедупликация, нормализация, watermark, MinIO Parquet. |
| 7 — Gold слой | `gold_tickers.py`, `gold_prices.py` — Airflow DAGs с ClickHouseOperator агрегируют Silver → `fact_tickers`, `dim_coin`, `fact_prices`. |

**Примечание:** `aggregation_dag.py` (SparkSubmit-подход для Gold через `gold_prices_aggregator.py`) заброшен. Gold агрегация работает через ClickHouse SQL — этого достаточно.

---

## Продвинутые фазы — Data Lakehouse

Цель: превратить набор Parquet-файлов и ClickHouse-таблиц в настоящий lakehouse с ACID-транзакциями, версионированием данных, контрактом схемы и observability.

---

### Фаза A — Apache Iceberg (Hadoop catalog) (2–3 дня)

**Зачем:** сейчас Silver/Gold в MinIO — просто набор Parquet-файлов без транзакций. Нет time-travel, нет schema evolution, нет атомарных записей. Iceberg решает всё это — без дополнительных сервисов, через Hadoop catalog (метаданные лежат прямо в MinIO).

**Компоненты:**

**1. Новых сервисов не нужно** — Hadoop catalog хранит метаданные Iceberg в S3 рядом с данными (`s3a://crypto-lake/iceberg/`). Никакого отдельного каталог-сервера.

**2. Iceberg пакеты для Spark** (`spark/Dockerfile` или `--packages` в spark-submit):
```
org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1
org.apache.hadoop:hadoop-aws:3.3.4
```

**3. Обновить `spark/jobs/utils/spark_session.py`** — добавить Iceberg конфиг:
```python
.config("spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
.config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
.config("spark.sql.catalog.lake.type", "hadoop")
.config("spark.sql.catalog.lake.warehouse", "s3a://crypto-lake/iceberg/")
```

**4. Переписать Silver writers** на Iceberg вместо `.parquet(path)`:
```python
# Было:
df.write.mode("overwrite").partitionBy("date").parquet("s3a://crypto-lake/silver/...")

# Стало — при первом запуске:
df.writeTo("lake.silver.tickers_clean") \
  .partitionedBy(F.days("event_time")) \
  .createOrReplace()

# При последующих (streaming micro-batch):
df.writeTo("lake.silver.tickers_clean").append()
```

**5. Gold агрегаторы не трогаем** — оставляем ClickHouse-агрегацию как есть. Iceberg ставим только на Silver (там streaming write), Gold пишем в ClickHouse напрямую.

**Проверка:**
```sql
-- Time-travel: данные час назад
SELECT * FROM lake.silver.tickers_clean
  TIMESTAMP AS OF TIMESTAMP '2026-05-10 10:00:00'
  LIMIT 10;

-- История снимков таблицы
SELECT * FROM lake.silver.tickers_clean.history;

-- Schema evolution: добавить колонку без перезаписи данных
ALTER TABLE lake.silver.tickers_clean ADD COLUMN spread_pct DOUBLE;
```

**Артефакт:** `SHOW TABLES IN lake.silver` показывает таблицы. В MinIO UI папка `iceberg/silver/tickers_clean/metadata/` содержит JSON-снимки. Time-travel работает.

---

### Фаза B — Schema Registry + Avro (2–3 дня)

**Зачем:** продьюсеры пишут JSON без контракта. Изменение поля в Bybit ответе ломает всю цепочку без предупреждения. Schema Registry даёт versioned контракт и валидацию на лету.

**1. Добавить Confluent Schema Registry** в compose:
```yaml
schema-registry:
  image: confluentinc/cp-schema-registry:7.7.1
  hostname: schema-registry
  environment:
    SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
    SCHEMA_REGISTRY_HOST_NAME: schema-registry
    SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
  ports:
    - "8082:8081"   # 8081 уже занят Spark Master на хосте
  depends_on:
    kafka:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8081/subjects"]
  restart: unless-stopped
```

**2. Зарегистрировать схемы** (в `infra/init-schema-registry.sh`):
```bash
# Avro схема для crypto.tickers (Bybit)
curl -X POST http://schema-registry:8081/subjects/crypto.tickers-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d @schemas/ticker_v1.avsc

# Avro схема для crypto.prices (CoinGecko)
curl -X POST http://schema-registry:8081/subjects/crypto.prices-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d @schemas/price_v1.avsc
```

Пример `schemas/ticker_v1.avsc`:
```json
{
  "type": "record",
  "name": "Ticker",
  "namespace": "crypto",
  "fields": [
    {"name": "symbol",       "type": "string"},
    {"name": "last_price",   "type": ["null", "double"], "default": null},
    {"name": "volume_24h",   "type": ["null", "double"], "default": null},
    {"name": "ts",           "type": "long", "logicalType": "timestamp-millis"},
    {"name": "exchange",     "type": "string", "default": "bybit"}
  ]
}
```

**3. Обновить продьюсеры** — `confluent_kafka.schema_registry.avro.AvroProducer` вместо `json.dumps`:
```python
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

sr_client = SchemaRegistryClient({"url": "http://schema-registry:8081"})
avro_serializer = AvroSerializer(sr_client, schema_str, to_dict=lambda obj, ctx: obj)
```

**4. Обновить `bronze_writer.py`** — читать через `from_avro()`:
```python
from pyspark.sql.avro.functions import from_avro

schema_str = requests.get("http://schema-registry:8081/subjects/crypto.tickers-value/versions/latest").json()["schema"]
df = kafka_df.select(from_avro(F.col("value"), schema_str).alias("data")).select("data.*")
```

> **Breaking change**: сначала тестировать на отдельном топике/бакете, убедиться что Bronze/Silver читают Avro корректно, только потом переключать prod топики.

**Артефакт:** `curl http://localhost:8082/subjects` — видим зарегистрированные схемы. При изменении поля в продьюсере без обновления схемы — получаем ошибку сериализации, а не тихие null-значения downstream.

---

### Фаза C — Prometheus + Grafana (2–3 дня)

**Зачем:** сейчас единственный способ понять состояние пайплайна — смотреть логи. Нужны метрики: Kafka lag, задержка батчей Spark, объём данных по слоям, ошибки DAG.

**1. Добавить в compose:**
```yaml
prometheus:
  image: prom/prometheus:v2.53.0
  ports:
    - "9090:9090"
  volumes:
    - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  restart: unless-stopped

grafana:
  image: grafana/grafana:11.1.0
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    GF_DATASOURCES_DEFAULT_URL: http://prometheus:9090
  volumes:
    - ./infra/grafana/dashboards:/var/lib/grafana/dashboards:ro
    - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
  restart: unless-stopped

clickhouse-exporter:
  image: f1yegor/clickhouse-exporter:latest
  environment:
    CLICKHOUSE_USER: default
    CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-clickhouse}
  ports:
    - "9116:9116"
  restart: unless-stopped
```

**2. Kafka метрики** — JMX exporter (`kafka-jmx-exporter`) → scrape в Prometheus:
- `kafka_consumer_group_lag` — лаг группы `clickhouse_tickers_consumer`
- `kafka_log_log_end_offset` — скорость записи

**3. Spark метрики** — добавить в `spark/jobs/utils/spark_session.py`:
```python
.config("spark.metrics.conf.*.sink.prometheusServlet.class",
        "org.apache.spark.metrics.sink.PrometheusServlet")
.config("spark.metrics.conf.*.sink.prometheusServlet.path", "/metrics/prometheus")
```
Метрики: `spark_streaming_batchDuration`, `spark_streaming_numInputRows`.

**4. Airflow метрики** через StatsD → prometheus-statsd-exporter:
```yaml
# airflow-env:
AIRFLOW__METRICS__STATSD_ON: "true"
AIRFLOW__METRICS__STATSD_HOST: statsd-exporter
AIRFLOW__METRICS__STATSD_PORT: 8125
```
Метрики: `airflow_dag_run_duration`, `airflow_task_failed_count`.

**5. ClickHouse** через `clickhouse-exporter`:
- `clickhouse_system_metrics_query` — активные запросы
- `clickhouse_system_parts_rows` — объём данных в таблицах

**Дашборды Grafana** (JSON provisioning в `infra/grafana/dashboards/`):

| Дашборд | Панели |
|---------|--------|
| Pipeline Health | Kafka lag (by topic), Bronze batch duration, Silver rows/sec, ClickHouse insert rate |
| Data Volume | Строк в Bronze/Silver/fact_tickers/fact_prices по времени (data growth) |
| Airflow | DAG success rate за 24h, последние failed tasks, avg task duration |
| ClickHouse | Query latency p50/p99, parts count, merges in progress |

**Алерты в Grafana:**
- Kafka lag > 10 000 → notify
- Spark batch duration > 120s → notify
- Airflow task failed → notify

**Артефакт:** Grafana `localhost:3000` — все 4 дашборда работают, метрики обновляются в реальном времени.

---

### Фаза D — Data Quality (1–2 дня)

**Зачем:** данные могут тихо деградировать (Bybit меняет формат, CoinGecko возвращает null) — нужны автоматические проверки.

**Инструмент:** SQL-чеки в Airflow как отдельные таски после каждого Silver и Gold шага.

**Добавить в Gold DAGs задачу-чекер:**
```python
from airflow_clickhouse_plugin.operators.clickhouse import ClickHouseOperator

quality_check_tickers = ClickHouseOperator(
    task_id="check_silver_tickers_freshness",
    sql="""
      SELECT throwIf(
        max(event_time) < now() - INTERVAL 10 MINUTE,
        'silver tickers stale: no data for 10 minutes'
      )
      FROM crypto.raw_tickers
    """,
    clickhouse_conn_id="clickhouse_default"
)

quality_check_prices = ClickHouseOperator(
    task_id="check_fact_prices_completeness",
    sql="""
      SELECT throwIf(
        countIf(current_price <= 0 OR current_price IS NULL) > 0,
        'fact_prices contains invalid prices'
      )
      FROM crypto.fact_prices
      WHERE date = today()
    """,
    clickhouse_conn_id="clickhouse_default"
)
```

**Стандартные проверки** добавить в каждый Gold DAG:
- Свежесть: `max(event_time) > now() - N minutes`
- Объём: `count() > expected_min_rows`
- Корректность: `countIf(price <= 0) = 0`
- Дубли: `count() = countDistinct(symbol, event_time)`

**Артефакт:** при деградации данных Gold DAG падает с понятным сообщением, а не тихо пишет мусор.

---

## Целевая архитектура

```
Bybit WebSocket ──────┐
                       ├──► Kafka (Avro + Schema Registry)
CoinGecko REST ────────┘          │
                           ┌──────▼──────────────┐
                           │  Spark Streaming    │
                           │  bronze_writer      │
                           └──────┬──────────────┘
                                  │ Bronze (Parquet)
                           ┌──────▼──────────────┐
                           │  Spark Streaming    │
                           │  silver_tickers     │
                           │  silver_prices      │
                           └──────┬──────────────┘
                                  │ Silver (Iceberg/Hadoop catalog)
                   ┌──────────────▼──────────────┐
                   │  Airflow DAGs               │
                   │  gold_tickers (ClickHouse)  │
                   │  gold_prices  (ClickHouse)  │
                   │  + quality checks           │
                   └──────────────┬──────────────┘
                                  │
Hot path:                  ┌──────▼──────────────┐
Kafka Engine → raw_tickers │  Superset           │
                           │  Grafana            │
                           └─────────────────────┘

Iceberg Hadoop catalog: time-travel, schema evolution (метаданные в MinIO)
Prometheus → Grafana: pipeline health, Kafka lag, DAG status
Schema Registry: versioned Avro schemas для всех топиков
```

---

## Приоритет

| # | Фаза | Дни | Ключевая ценность |
|---|------|-----|-------------------|
| A | Iceberg (Hadoop catalog) | 2–3 | ACID, time-travel, schema evolution |
| B | Schema Registry | 2–3 | Контракт данных, безопасные изменения схемы |
| C | Prometheus + Grafana | 2–3 | Observability, алерты |
| D | Data Quality | 1–2 | SLA, раннее обнаружение деградации |

**Итого:** ~7–11 рабочих дней.

---

## Feature Store — проектное предложение

> Не входит в план реализации, но логично ложится поверх готового lakehouse.

**Что такое Feature Store в контексте этого проекта:**
Централизованное хранилище вычисленных ML-фич (RSI, MACD, SMA, волатильность, returns, cross-asset корреляции) с двумя хранилищами:
- **Offline store** (MinIO/Iceberg Hadoop catalog) — исторические фичи для обучения моделей
- **Online store** (ClickHouse или Redis) — последние значения для low-latency inference

**Стек:** [Feast](https://feast.dev/) как фреймворк (умеет MinIO + Redis/ClickHouse из коробки) или кастомная реализация.

**Архитектура:**

```
Silver (Iceberg/Hadoop) ──► Spark batch job ──► Feature Engineering
                       (Airflow, @hourly)      │
                                        ┌──────┴───────────┐
                                        │                  │
                               Offline Store        Online Store
                            (MinIO/Iceberg        (ClickHouse)
                            Hadoop catalog)
                            исторические фичи   последние N строк
                            для train/backtest   для inference
```

**Фичи для крипто:**
```python
# Ценовые индикаторы (окно на Silver тикерах)
- sma_10, sma_20, sma_50          # скользящие средние
- rsi_14                           # Relative Strength Index
- macd_signal, macd_hist           # MACD
- bollinger_upper, bollinger_lower # Bollinger Bands
- atr_14                           # Average True Range (волатильность)

# Объёмные фичи
- volume_sma_10                    # средний объём
- volume_ratio                     # текущий объём / средний

# Межактивные фичи (из fact_prices)
- btc_dominance                    # доля BTC в капитализации
- corr_btc_eth_7d                  # корреляция BTC/ETH за 7 дней

# Лаги
- return_1h, return_24h, return_7d # % изменение цены
```

**Spark job** `spark/jobs/feature_engineering.py` (запуск из Airflow `@hourly`):
```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

window_14 = Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-13, 0)

features = silver_tickers \
    .withColumn("sma_10", F.avg("last_price").over(
        Window.partitionBy("symbol").orderBy("event_time").rowsBetween(-9, 0)
    )) \
    .withColumn("return_1h", (F.col("last_price") - F.lag("last_price", 60).over(
        Window.partitionBy("symbol").orderBy("event_time")
    )) / F.lag("last_price", 60).over(...)) \
    ...

# Offline store
features.writeTo("nessie.features.crypto_features").append()

# Online store — только последний снимок
features \
    .groupBy("symbol") \
    .agg(F.max_by(F.struct("*"), "event_time").alias("latest")) \
    .select("latest.*") \
    .write.mode("overwrite") \
    .jdbc(clickhouse_url, "crypto.features_online", properties=clickhouse_props)
```

**Airflow DAG** `feature_store_refresh.py`:
```
silver_freshness_check >> feature_engineering >> quality_check_features >> notify
```

**ClickHouse online store схема:**
```sql
CREATE TABLE crypto.features_online (
    symbol         LowCardinality(String),
    as_of_time     DateTime64(3, 'UTC'),
    sma_10         Nullable(Float64),
    sma_20         Nullable(Float64),
    rsi_14         Nullable(Float64),
    macd_hist      Nullable(Float64),
    return_1h      Nullable(Float64),
    return_24h     Nullable(Float64),
    volume_ratio   Nullable(Float64)
) ENGINE = ReplacingMergeTree(as_of_time)
ORDER BY symbol;
```

**Point-in-time join** для обучения (из offline store):
```python
# Чтобы не было data leakage при backtest —
# для каждого события берём фичи, которые были известны ДО этого момента
features_pit = labels.join(
    offline_features,
    on=(labels.symbol == offline_features.symbol) &
       (offline_features.as_of_time <= labels.event_time),
    how="left"
).where(F.rank().over(
    Window.partitionBy("label_id").orderBy(F.desc("as_of_time"))
) == 1)
```

**Почему Feature Store имеет смысл именно здесь:**
- Iceberg offline store даёт time-travel → point-in-time корректные фичи для backtest
- ClickHouse online store даёт <10ms latency для inference
- Airflow уже есть → просто добавить ещё один DAG
- Все исходные данные уже очищены в Silver → минимальная доп. работа

---

## Что важнее не пропустить

1. **Идемпотентность** — `ReplacingMergeTree`, `dropDuplicates`, Kafka ключи по symbol.
2. **Iceberg checkpoint** — хранить в S3, не в локальной FS контейнера.
3. **LowCardinality(String)** в ClickHouse для symbol/exchange — критично для производительности.
4. **maxOffsetsPerTrigger** в Spark — защита от backpressure при рестарте.
5. **Структурированные логи** (JSON) с topic/partition/offset — единственный способ дебажить streaming.
6. **Iceberg schema evolution** — `ALTER TABLE lake.silver.X ADD COLUMN` не требует перезаписи данных, старые файлы читаются с null в новых колонках.
