#!/bin/bash
# Первый выпуск SSL-сертификата Let's Encrypt для домена из .env
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Create .env first (cp .env.example .env)" >&2
  exit 1
fi

set -a
source .env
set +a

if [ -z "${DOMAIN:-}" ] || [ -z "${CERTBOT_EMAIL:-}" ]; then
  echo "Set DOMAIN and CERTBOT_EMAIL in .env" >&2
  exit 1
fi

echo "==> Starting base stack..."
docker compose --profile bundled-nginx up -d postgres redis web

echo "==> Starting nginx (HTTP, for ACME challenge)..."
docker compose --profile bundled-nginx up -d nginx

echo "==> Requesting certificate for ${DOMAIN}..."
docker compose --profile bundled-nginx exec nginx certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${CERTBOT_EMAIL}" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

echo "==> Restarting nginx with SSL..."
docker compose --profile bundled-nginx restart nginx

echo "Done. Site should be available at https://${DOMAIN}/"
echo "Auto-renewal runs inside nginx container every 12 hours."
