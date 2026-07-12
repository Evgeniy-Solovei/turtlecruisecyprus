#!/usr/bin/env bash
# Switch local dev from SQLite to PostgreSQL (Docker).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Starting Postgres + Redis..."
docker compose up -d postgres redis

export DATABASE_URL="${DATABASE_URL:-postgresql://turtlecruise:turtlecruise@localhost:5432/turtlecruise}"

if [[ -f .env ]]; then
  if grep -q '^DATABASE_URL=' .env; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env
    else
      sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env
    fi
  else
    echo "DATABASE_URL=$DATABASE_URL" >> .env
  fi
else
  cp .env.example .env
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env
  else
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" .env
  fi
fi

echo "Waiting for Postgres..."
until docker compose exec -T postgres pg_isready -U turtlecruise -d turtlecruise >/dev/null 2>&1; do
  sleep 1
done

source .venv/bin/activate
python manage.py migrate

cat <<EOF

PostgreSQL is ready.

DATABASE_URL=$DATABASE_URL

If you had data only in SQLite, re-import content:
  python manage.py import_wp_site --sql ../turtlecruisebyscubacat/dup-installer/dup-database__....sql
  python manage.py import_wp_bookings
  python manage.py createsuperuser

EOF
