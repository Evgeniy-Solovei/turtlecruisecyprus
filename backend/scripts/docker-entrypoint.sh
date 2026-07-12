#!/bin/bash
set -euo pipefail

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "==> Waiting for database..."
  python <<'PY'
import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()
from django.db import connection

for attempt in range(30):
    try:
        connection.ensure_connection()
        print("Database is ready.")
        break
    except Exception as exc:
        print(f"Database not ready ({attempt + 1}/30): {exc}")
        time.sleep(2)
else:
    sys.exit("Database connection failed.")
PY

  echo "==> Checking pending migrations..."
  python manage.py showmigrations --plan | tee /tmp/migration-plan.log
  if grep -q '\[ \]' /tmp/migration-plan.log; then
    echo "Unapplied migrations detected — running migrate..."
  else
    echo "No pending migrations."
  fi

  echo "==> Applying migrations..."
  python manage.py migrate --noinput

  if python manage.py showmigrations --plan | grep -q '\[ \]'; then
    echo "ERROR: migrations still pending after migrate." >&2
    exit 1
  fi

  echo "==> Collecting static files (whitenoise)..."
  python manage.py collectstatic --noinput
else
  echo "==> Skipping migrations/collectstatic (RUN_MIGRATIONS!=1)"
fi

exec "$@"
