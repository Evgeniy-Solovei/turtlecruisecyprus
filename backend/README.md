# Turtle Cruise Django backend

Backend scaffold for replacing the current WordPress/MotoPress booking flow.

## Stack

- Django + Django REST Framework
- Django Unfold for custom admin UI
- PostgreSQL in production, SQLite allowed for local smoke tests
- Celery + Redis
- Stripe PaymentIntent + signed webhooks
- Brevo email delivery
- ClickSend SMS delivery

## Local setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Optional: PostgreSQL + Redis via Docker (recommended — same as production)
docker compose up -d
chmod +x scripts/migrate-to-postgres.sh
./scripts/migrate-to-postgres.sh

# Production stack (gunicorn + whitenoise + celery):
# docker compose -f docker-compose.prod.yml up -d --build

python manage.py migrate
python manage.py import_wp_bookings
python manage.py createsuperuser
python manage.py runserver
```

In another terminal (optional, for timers and notifications):

```bash
cd backend && source .venv/bin/activate
celery -A config worker -l info
celery -A config beat -l info
```

The repository root contains `.turtlecruise_secrets.local.env`. It is ignored by git and is loaded automatically by `config/settings/base.py`. Do not commit it and do not paste its values into chats or tickets.

## Import WordPress data

```bash
python manage.py import_wp_bookings
python manage.py compare_wp_django_availability --date 2026-07-10
```

The importer is intentionally conservative. It creates the core Django objects and preserves legacy IDs for repeated imports and manual verification.

## Production (Docker + uvicorn + whitenoise)

```bash
cd backend
cp .env.example .env
# Заполни DATABASE_URL, STRIPE_*, BREVO_*, DJANGO_SECRET_KEY, SITE_BASE_URL, DJANGO_ALLOWED_HOSTS

docker compose -f docker-compose.prod.yml up -d --build
```

При старте контейнера `web` автоматически:
1. ждёт Postgres
2. проверяет неприменённые миграции и запускает `migrate`
3. собирает статику (`collectstatic`) для **WhiteNoise** (админка + CSS/JS)

Стек: `web` (uvicorn, 3 workers) + `worker` + `beat` + `postgres` + `redis`.

Логи: `docker compose -f docker-compose.prod.yml logs -f web`

**Полная инструкция по деплою, ключам, DNS Brevo, Postgres:** [docs/DEPLOY.md](../docs/DEPLOY.md)  
**Git без секретов:** [docs/GIT.md](../docs/GIT.md)

## Аналитика и логирование

Клиентский трекинг подключён глобально (`site-tracking.js` в `base.html`):
- время на каждой странице (`PageView`)
- глубина скролла
- шаги воронки бронирования (`JourneyEvent`)

API (только для админа, кроме POST events):
```text
POST /api/v1/audit/events/          — события с фронта (без CSRF, sendBeacon OK)
GET  /api/v1/audit/funnel/?days=7   — воронка + топ страниц по времени
GET  /api/v1/audit/sessions/{id}/   — полный путь сессии
GET  /api/v1/bookings/{id}/trace/   — цепочка брони (включая page views)
```

Админка: **Аудит** → Просмотры страниц / Сессии / Воронка.


Admin URL:

```text
http://127.0.0.1:8000/admin/
```

The admin uses Django Unfold and Russian labels for models and fields. Main sections:

- Брони
- Клиенты
- Платежи
- Круизы
- Расписания
- Исключения дат
- Email/SMS логи
- Webhook логи
- Настройки

## API

Swagger UI: http://127.0.0.1:8000/api/docs/

Подробная документация:
- [docs/API.md](../docs/API.md)
- [docs/BOOKING_CHAIN.md](../docs/BOOKING_CHAIN.md) — цепочка брони и точки логирования

```text
GET  /api/v1/cruises/
GET  /api/v1/cruises/{code}/availability/?date=YYYY-MM-DD
POST /api/v1/bookings/hold/
GET  /api/v1/bookings/{public_id}/
GET  /api/v1/bookings/{public_id}/trace/   ← полная цепочка логов
POST /api/v1/bookings/{public_id}/cancel/
POST /api/v1/payments/stripe/payment-intent/
POST /api/v1/payments/stripe/confirm/
POST /api/v1/payments/stripe/webhook/
POST /api/v1/audit/events/
POST /wp-admin/admin-ajax.php
```

The WordPress compatibility endpoint supports the old AJAX action names so the current booking popup can be moved gradually.
