# План разработки CryptoFlow MVP

**Принцип:** каждая фаза заканчивается работающим end-to-end куском, который можно показать. Не идём дальше, пока предыдущая фаза не работает.

**Стек MVP** (минимальный, но честный):
Kafka 4.1 (KRaft) → Spark 3.5.5 Structured Streaming → MinIO (Parquet) + ClickHouse 25.8 → Superset 5.0. Оркестрация — Airflow 3.2.1.

Из README выкинуто для MVP: Iceberg (вместо него обычный партиционированный Parquet), dbt (трансформации делаем в Spark + materialized views в ClickHouse), Prometheus/Grafana, корреляции/ML feature store, replay-механизм. Эти штуки добавляются после фазы 6 как «продвинутые».

---

## Фаза 0 — Инфраструктура (1–2 дня)

**Цель:** `docker compose up -d` поднимает весь стек, все сервисы healthy.

- Запустить compose. Проверить UI: MinIO (9001), Kafka UI опционально, ClickHouse (8123), Airflow (8080), Superset (8088), Spark Master (8081).
- Убедиться, что бакеты в MinIO и топики в Kafka созданы init-контейнерами.
- ClickHouse: подключиться через `clickhouse-client`, проверить созданные базы.

**Артефакт:** видео/скрин с работающими сервисами.

---

## Фаза 1 — Один продьюсер (2–3 дня)

**Цель:** реальные данные текут в Kafka.

- Реализовать `producers/binance_ws_producer.py` — WebSocket-клиент к `wss://stream.binance.com:9443/ws/!ticker@arr` (поток всех тикеров).
- Сериализация в JSON, ключ Kafka = `symbol`, топик `crypto.tickers`.
- Reconnect с exponential backoff. Логирование событий в секунду.
- Поднять контейнер `producer-binance` в compose.
- Проверить: `docker exec kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic crypto.tickers --from-beginning | head` — видим JSON.

---

## Фаза 2 — Bronze слой (3–4 дня)

**Цель:** сырые данные оседают в S3 (MinIO) как партиционированный Parquet.

- `spark/jobs/bronze_writer.py` — Structured Streaming job: читает из Kafka, парсит JSON, добавляет `ingestion_ts`, `kafka_offset`, пишет в `s3a://crypto-lake/bronze/tickers/year=YYYY/month=MM/day=DD/hour=HH/`.
- Trigger: `processingTime="30 seconds"`. Checkpoint в S3.
- Запустить как long-running контейнер `spark-bronze` через `spark-submit --master spark://spark-master:7077`.
- Проверить через MinIO UI: появились партиции и parquet-файлы.

**Чему учишься:** Spark Structured Streaming, S3A, partition pruning, checkpointing.

---

## Фаза 3 — Hot path: Kafka → ClickHouse (2 дня)

**Цель:** данные доступны для запросов почти в real-time, без ожидания Spark batch.

- В ClickHouse создать `Kafka Engine` таблицу + `Materialized View` + `MergeTree` приёмник (`crypto.raw_tickers`). Это уже в `clickhouse/init/01_schema.sql`.
- Проверить `SELECT count(), max(event_time) FROM crypto.raw_tickers` — счётчик растёт, lag минимальный.

**Чему учишься:** ClickHouse Kafka engine, materialized views, столбцовое хранилище.

---

## Фаза 4 — Superset дашборд (1–2 дня)

**Цель:** визуализация в браузере.

- Подключить ClickHouse как datasource в Superset (DSN: `clickhousedb://default:<pwd>@clickhouse:8123/crypto`).
- Сделать dataset на `crypto.raw_tickers`.
- Дашборд «Market Live»: line chart цен топ-5 пар за последний час, scorecard «events/sec», таблица с последними тиками.

---

## Фаза 5 — Второй продьюсер + Airflow batch (3–4 дня)

**Цель:** учимся оркестрировать.

- `producers/coingecko_polling_producer.py` — REST polling каждые 60 сек, топик `crypto.prices`.
- Поднимаем как ещё один контейнер либо запускаем периодически из Airflow.
- Airflow DAG `coingecko_ohlcv_backfill.py`: ежедневно тянет дневные свечи топ-50 монет за последние 2 дня → публикует в `crypto.ohlcv`.
- Airflow DAG `fear_greed_daily.py`: ежедневно тянет F&G index → `crypto.sentiment`.
- В ClickHouse добавляем приёмники для OHLCV и sentiment по аналогии с тикерами.

**Чему учишься:** Airflow 3 TaskFlow API, batch vs streaming, идемпотентные джобы.

---

## Фаза 6 — Silver слой в Spark (4–5 дней)

**Цель:** чистые, дедуплицированные данные.

- `spark/jobs/silver_processor.py` — Structured Streaming читает Bronze (через Auto-Loader-style file source), делает:
  - нормализацию символов (`BTCUSDT` → `BTC_USDT`),
  - дедупликацию `dropDuplicates(["symbol", "event_time"])` с watermark 10 минут,
  - фильтр аномалий (price <= 0).
- Пишет в `s3a://crypto-lake/silver/tickers_clean/` партиционированно по дате.
- Запускаем как ещё один long-running контейнер `spark-silver`.

**Чему учишься:** watermarking, late-arriving data, файловый стрим как источник.

---

## Фаза 7 — Gold + ClickHouse upsert (3–4 дня)

**Цель:** готовые агрегаты для аналитики.

- `spark/jobs/gold_aggregator.py` (запуск из Airflow ежечасно): читает Silver, считает OHLCV по 1m/5m/1h/1d свечам, простые индикаторы (SMA10, SMA20).
- Загружает результат в ClickHouse `crypto.asset_metrics` через JDBC (`spark.write.format("jdbc")`).
- Airflow DAG `gold_refresh_hourly.py` оркестрирует.

---

## Дальше — продвинутые фазы (когда базу ты сделал)

- **Iceberg** на Silver/Gold вместо обычного Parquet — ACID, time-travel, schema evolution. Ставится через `--packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1`.
- **dbt-clickhouse** — переносим логику из Spark Gold aggregator в dbt models, получаем тесты + lineage.
- **ML feature store** — Spark джоба собирает фичи (RSI, MACD, лаги, on-chain метрики), пишет в отдельную ClickHouse-таблицу.
- **Replay** — параметризованный DAG в Airflow, который запускает Spark batch (`Trigger.AvailableNow`) на исторических Bronze-партициях.
- **Prometheus + Grafana** — JMX exporter для Kafka, Spark UI metrics, ClickHouse system tables.
- **Schema Registry + Avro** — когда надоест чинить сломанные JSON-схемы.

---

## Что важнее не пропустить (от Senior DE)

1. **Идемпотентность** — каждый продьюсер/джоба должна корректно обрабатывать повторный запуск без дублей. ClickHouse `ReplacingMergeTree`, Spark `dropDuplicates`, Kafka ключи по symbol.
2. **Checkpointing** Spark Streaming в S3, не в local fs контейнера. Иначе при рестарте теряется прогресс.
3. **Кардинальность** в ClickHouse — `LowCardinality(String)` для symbol/exchange. Это +10x скорость.
4. **Партиционирование** в S3 = partition pruning в Spark. По дате/часу — оптимально для дневных и часовых джоб.
5. **Backpressure** — Spark `maxOffsetsPerTrigger`, продьюсеры с rate limiting.
6. **Логирование** — структурированные логи (JSON) с указанием topic/partition/offset для дебага.
