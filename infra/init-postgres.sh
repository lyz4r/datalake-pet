#!/bin/bash
set -e

# Postgres official image runs all .sh files in /docker-entrypoint-initdb.d/.
# This creates the additional databases listed in POSTGRES_MULTIPLE_DATABASES.

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
  for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
    if [ "$db" != "$POSTGRES_USER" ]; then
      echo "[postgres-init] Creating database: $db"
      psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $db OWNER $POSTGRES_USER;
EOSQL
    fi
  done
fi
