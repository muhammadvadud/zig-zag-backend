#!/usr/bin/env bash
set -e

# Wait for Postgres before running migrations.
if [ -n "$POSTGRES_HOST" ]; then
  echo "Waiting for postgres at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
  echo "Postgres is up."
fi

# Only the web service should run migrations / collectstatic.
if [ "$RUN_MIGRATIONS" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
