# Развёртывание Turtle Cruise (staging → production)

Пошаговая инструкция: сервер, ключи, DNS, Brevo, Stripe, тестовая вместимость 3 места.

---

## 1. Что где лежит

| Что | Где настраивать |
|-----|-----------------|
| Все секреты (Stripe, Brevo, Django) | `backend/.env` на сервере (не в git!) |
| Legacy-секреты из WP (опционально) | `.turtlecruise_secrets.local.env` в корне репо (локально, не в git) |
| Шаблон без секретов | `backend/.env.example` |
| Docker production | `backend/docker-compose.prod.yml` |
| Postgres + Redis локально | `backend/docker-compose.yml` |
| SSL/nginx | `backend/deploy/nginx/`, `backend/scripts/init-ssl.sh` |

---

## 2. Переход на PostgreSQL

### Локально (Mac)

```bash
cd backend
source .venv/bin/activate
chmod +x scripts/migrate-to-postgres.sh
./scripts/migrate-to-postgres.sh
```

Скрипт:
1. Поднимает Postgres + Redis в Docker
2. Прописывает `DATABASE_URL` в `.env`
3. Запускает `migrate`

Если раньше работал только SQLite — **данные в Postgres пустые**. Нужен повторный импорт:

```bash
python manage.py import_wp_site --sql ../turtlecruisebyscubacat/dup-installer/dup-database__46e869c-06090919.sql
python manage.py import_wp_bookings
python manage.py createsuperuser
```

### На сервере (Docker prod)

Postgres уже в `docker-compose.prod.yml`. В `.env` на сервере **не нужно** отдельно задавать `DATABASE_URL` — compose подставляет:

```
postgresql://turtlecruise:turtlecruise@postgres:5432/turtlecruise
```

Пароль поменять: правка `POSTGRES_PASSWORD` в `docker-compose.prod.yml` + `DATABASE_URL` у сервисов `web/worker/beat`.

---

## 3. Staging: полный запуск

### 3.1 Сервер

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# перелогиниться
```

### 3.2 Клонирование

```bash
git clone <URL-репозитория> /opt/turtlecruise
cd /opt/turtlecruise/backend
cp .env.example .env
nano .env   # заполнить по таблице ниже
```

### 3.3 DNS (для staging)

У регистратора домена:

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | `staging` | IP вашего VPS | 300 |

Проверка: `dig staging.turtlecruisecyprus.com +short` → должен вернуть IP сервера.

В `.env`:

```env
DOMAIN=staging.turtlecruisecyprus.com
DJANGO_ALLOWED_HOSTS=staging.turtlecruisecyprus.com,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.turtlecruisecyprus.com
SITE_BASE_URL=https://staging.turtlecruisecyprus.com
CERTBOT_EMAIL=book@turtlecruisecyprus.com
```

### 3.4 Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
chmod +x scripts/init-ssl.sh
./scripts/init-ssl.sh
```

После SSL в `.env`:

```env
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
DJANGO_SETTINGS_MODULE=config.settings.staging
```

```bash
docker compose -f docker-compose.prod.yml restart web
```

### 3.5 Импорт контента

```bash
# Скопировать SQL-дамп на сервер (не коммитить в git!)
docker compose -f docker-compose.prod.yml exec web python manage.py import_wp_site \
  --sql /path/on/server/dup-database__....sql

docker compose -f docker-compose.prod.yml exec web python manage.py import_wp_bookings
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Медиа (фото): скопировать `backend/media/wp/` на сервер в volume `media_data` или примонтировать при первом деплое.

---

## 4. Ключи и сервисы — что куда в `.env`

### Django (обязательно)

```env
DJANGO_SETTINGS_MODULE=config.settings.staging   # staging; production → config.settings.production
DJANGO_SECRET_KEY=<случайная строка 50+ символов>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=staging.turtlecruisecyprus.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.turtlecruisecyprus.com
SITE_BASE_URL=https://staging.turtlecruisecyprus.com
```

Сгенерировать секрет:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Stripe (тест на staging)

```env
STRIPE_MODE=test
STRIPE_TEST_PUBLIC_KEY=pk_test_...
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Где взять:
- [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/test/apikeys) (test mode)
- Webhook: Dashboard → Webhooks → Add endpoint  
  URL: `https://staging.turtlecruisecyprus.com/api/v1/payments/stripe/webhook/`  
  События: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.succeeded`, `payment_intent.payment_failed`

Или с ноутбука:

```bash
stripe listen --forward-to https://staging.turtlecruisecyprus.com/api/v1/payments/stripe/webhook/
```

### Brevo (email)

```env
BREVO_API_KEY=xkeysib-...
BREVO_SENDER_EMAIL=book@turtlecruisecyprus.com
BREVO_SENDER_NAME=Turtle Cruise Cyprus
ADMIN_EMAIL_RECIPIENTS=book@turtlecruisecyprus.com
```

Опционально SMTP (если API не используется):

```env
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USERNAME=<логин из Brevo>
BREVO_SMTP_PASSWORD=<SMTP key из Brevo>
```

#### DNS для Brevo (чтобы письма не в спам)

В панели [Brevo → Senders & Domains → Domains](https://app.brevo.com/senders/domain/list) добавьте `turtlecruisecyprus.com`. Brevo покажет записи — добавьте у регистратора DNS:

| Тип | Имя | Значение (пример — берите из Brevo!) |
|-----|-----|--------------------------------------|
| TXT | `@` или домен | SPF: `v=spf1 include:sendinblue.com ~all` |
| TXT | `mail._domainkey` | DKIM — длинная строка из Brevo |
| CNAME | `brevo1._domainkey` | из Brevo |
| CNAME | `brevo2._domainkey` | из Brevo |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:book@turtlecruisecyprus.com` (опционально) |

После добавления записей в Brevo нажмите **Verify**. Обычно 15 мин – 48 ч.

Отправитель `book@turtlecruisecyprus.com` должен быть подтверждён в Brevo (Senders).

### ClickSend (SMS, опционально)

```env
CLICKSEND_USERNAME=...
CLICKSEND_API_KEY=...
CLICKSEND_SENDER_ID=...
ADMIN_SMS_RECIPIENTS=+357...
ADMIN_NOTIFY_CHANNEL=sms
```

### Telegram (альтернатива SMS)

```env
ADMIN_NOTIFY_CHANNEL=telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ADMIN_CHAT_IDS=123456789
```

### Redis / Celery

На сервере в Docker уже настроено. Локально:

```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### GTM (позже)

```env
GTM_CONTAINER_ID=GTM-K63GCMLB
```

---

## 5. Тест «мест нет» — вместимость 3 места

Чтобы не делать 40 броней, на **staging** временно:

```bash
# Локально
python manage.py set_cruise_capacity 3

# На сервере
docker compose -f docker-compose.prod.yml exec web python manage.py set_cruise_capacity 3
```

Вернуть обратно (например 30):

```bash
python manage.py set_cruise_capacity 30
```

Или в админке: **Круизы** → Morning / Sunset → поле «Базовая вместимость».

Логика: только **confirmed** брони занимают места; pending не блокируют до оплаты.

---

## 6. Чеклист тестирования

| # | Проверка |
|---|----------|
| 1 | Главная, EN/DE, меню как на проде |
| 2 | `/gallery/` — все фото грузятся |
| 3 | Бронь → Stripe test `4242 4242 4242 4242` → thank-you |
| 4 | 3 confirmed брони на дату → sold out |
| 5 | Email в Brevo / лог в админке **Email логи** |
| 6 | Webhook Stripe в Dashboard — 200 OK |
| 7 | `/admin/` — брони, аудит |
| 8 | `docker compose -f docker-compose.prod.yml logs -f worker beat` |

---

## 7. Production cutover

1. Скопировать рабочий `.env` staging → поменять домен на `turtlecruisecyprus.com`
2. `STRIPE_MODE=live` + live keys + **новый** webhook на prod URL
3. DNS A-запись основного домена → IP сервера
4. `./scripts/init-ssl.sh` с `DOMAIN=turtlecruisecyprus.com`
5. Brevo DNS уже на домене — менять не нужно

Подробнее staging: [STAGING.md](./STAGING.md)  
Git без секретов: [GIT.md](./GIT.md)
