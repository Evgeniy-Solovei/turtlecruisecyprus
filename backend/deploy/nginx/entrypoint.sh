#!/bin/sh
set -eu

DOMAIN="${DOMAIN:-}"
export DOMAIN

if [ -z "$DOMAIN" ]; then
  echo "ERROR: DOMAIN env var is required for nginx." >&2
  exit 1
fi

CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
if [ -f "$CERT_PATH" ]; then
  envsubst '${DOMAIN}' < /etc/nginx/templates/ssl.conf.template > /etc/nginx/conf.d/default.conf
  echo "nginx: SSL mode (${DOMAIN})"
else
  envsubst '${DOMAIN}' < /etc/nginx/templates/http.conf.template > /etc/nginx/conf.d/default.conf
  echo "nginx: HTTP-only mode (${DOMAIN}) — run scripts/init-ssl.sh to get certificate"
fi

if [ -f "$CERT_PATH" ]; then
  (
    while true; do
      sleep 12h
      certbot renew --quiet --webroot -w /var/www/certbot && nginx -s reload
      echo "certbot: renewal check done at $(date -Iseconds)"
    done
  ) &
fi

exec nginx -g 'daemon off;'
