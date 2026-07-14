#!/bin/bash
set -euo pipefail

mkdir -p /app/staticfiles /app/media
chown -R appuser:appuser /app/staticfiles /app/media

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "==> Waiting for database..."
  gosu appuser python <<'PY'
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
  gosu appuser python manage.py showmigrations --plan | tee /tmp/migration-plan.log
  if grep -q '\[ \]' /tmp/migration-plan.log; then
    echo "Unapplied migrations detected — running migrate..."
  else
    echo "No pending migrations."
  fi

  echo "==> Applying migrations..."
  gosu appuser python manage.py migrate --noinput

  if gosu appuser python manage.py showmigrations --plan | grep -q '\[ \]'; then
    echo "ERROR: migrations still pending after migrate." >&2
    exit 1
  fi

  echo "==> Syncing site content from git (CMS snapshot + images)..."
  gosu appuser python manage.py ensure_site_assets

  # After assets are in place: clear STATIC_ROOT and rebuild with content hashes.
  # {% static %} then points to new hashed URLs → browsers fetch fresh JS/CSS without hard refresh.
  echo "==> Rebuilding static files (hashed collectstatic)..."
  gosu appuser python manage.py collectstatic --noinput --clear
else
  echo "==> Skipping migrations/collectstatic (RUN_MIGRATIONS!=1)"
fi

exec gosu appuser "$@"
