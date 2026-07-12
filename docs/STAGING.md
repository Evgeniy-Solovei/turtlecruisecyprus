# Staging deployment (test server before production cutover)

**Полная инструкция:** [DEPLOY.md](./DEPLOY.md) (ключи, Brevo DNS, Postgres, 3 места для теста).  
**Git:** [GIT.md](./GIT.md).

Use a **separate subdomain**, e.g. `staging.turtlecruisecyprus.com` or `test.yourdomain.com`.
Run the **same Docker stack** as production with **Stripe test keys** and **Brevo** (or console email).

## 1. Server prep

```bash
# On VPS (Ubuntu/Debian)
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# re-login
```

## 2. Clone and configure

```bash
git clone <your-repo> /opt/turtlecruise
cd /opt/turtlecruise/backend
cp .env.example .env
```

Edit `.env` for staging:

```env
DJANGO_SETTINGS_MODULE=config.settings.staging
DJANGO_SECRET_KEY=<long-random-string>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=staging.turtlecruisecyprus.com,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.turtlecruisecyprus.com
SITE_BASE_URL=https://staging.turtlecruisecyprus.com

STRIPE_MODE=test
STRIPE_TEST_PUBLIC_KEY=pk_test_...
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...   # from stripe listen or Dashboard webhook

SECURE_SSL_REDIRECT=false          # true after nginx+SSL
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false

BREVO_API_KEY=...
BREVO_SENDER_EMAIL=book@turtlecruisecyprus.com
GTM_CONTAINER_ID=GTM-K63GCMLB
```

## 3. Start stack + SSL

DNS: A-запись `staging` → IP сервера (должна указывать на сервер **до** выпуска сертификата).

```bash
docker compose -f docker-compose.prod.yml up -d --build
chmod +x scripts/init-ssl.sh
./scripts/init-ssl.sh
```

Скрипт:
1. поднимает web + nginx на HTTP
2. получает сертификат Let's Encrypt (бесплатно, на 90 дней)
3. перезапускает nginx с HTTPS

**Автопродление:** внутри контейнера `nginx` каждые 12 часов `certbot renew` + reload.

После SSL в `.env` включи:

```env
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

И перезапусти web: `docker compose -f docker-compose.prod.yml restart web`

On first start the `web` container automatically:
- waits for Postgres
- runs `migrate` (fails if migrations pending)
- runs `collectstatic` (WhiteNoise + admin static)

Import content (one-time or after template changes):

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py import_wp_site \
  --sql /path/to/dup-database__....sql
docker compose -f docker-compose.prod.yml exec web python manage.py import_wp_bookings
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 4. nginx + SSL (встроено в Docker)

См. шаг 3 выше — отдельный nginx на хосте **не нужен**.
Контейнер `nginx` проксирует на `web:8000`, раздаёт `/static/` и `/media/`, выпускает и продлевает SSL.

## 5. Stripe webhooks on staging

**Option A — Stripe CLI** (from your laptop):

```bash
stripe listen --forward-to https://staging.turtlecruisecyprus.com/api/v1/payments/stripe/webhook/
```

**Option B — Dashboard**: add endpoint URL on staging domain, copy `whsec_` to `.env`, restart web.

## 6. Test checklist

| # | Test |
|---|------|
| 1 | Home, EN/DE pages, language switcher |
| 2 | `/sitemap.xml`, `/robots.txt` |
| 3 | Blog article at `/<slug>/` (not only `/blog/<slug>/`) |
| 4 | Booking popup → hold → Stripe test card `4242...` → thank-you |
| 5 | Admin `/admin/` — booking confirmed, emails logged |
| 6 | `GET /api/v1/audit/funnel/?days=7` (admin session) |
| 7 | Cookie banner → Accept → GTM loads |
| 8 | Celery worker logs: `docker compose -f docker-compose.prod.yml logs -f worker beat` |

## 7. Switch to production

1. Copy working `.env`, change `SITE_BASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
2. `STRIPE_MODE=live` + live keys + new webhook endpoint on prod domain
3. DNS A-record for main domain → same server (or new)
4. Submit `sitemap.xml` in Google Search Console
5. Keep **301 redirects** — old WP URLs must still work

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web worker beat
```

## Rollback

Point DNS back to WordPress. Django staging remains for debugging.
