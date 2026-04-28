#!/bin/sh
set -e

echo "[minio-init] Waiting for MinIO..."
until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done

echo "[minio-init] Creating buckets..."
mc mb -p local/crypto-lake          || true
mc mb -p local/spark-checkpoints    || true
mc mb -p local/iceberg-warehouse    || true

echo "[minio-init] Buckets:"
mc ls local

echo "[minio-init] Done."
