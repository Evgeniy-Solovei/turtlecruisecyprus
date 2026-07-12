from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BASE_DIR.parent

load_dotenv(REPO_DIR / ".turtlecruise_secrets.local.env")
load_dotenv(BASE_DIR / ".env")
load_dotenv(REPO_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "local-dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.cruises",
    "apps.bookings",
    "apps.payments",
    "apps.notifications",
    "apps.migration_wp",
    "apps.audit",
    "apps.frontend",
    "apps.cms",
]

UNFOLD = {
    "SITE_TITLE": "Turtle Cruise Admin",
    "SITE_HEADER": "Turtle Cruise Cyprus",
    "SITE_SUBHEADER": "Бронирования, оплаты и уведомления",
    "SITE_SYMBOL": "directions_boat",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "ENVIRONMENT": "config.settings.base.environment_callback",
    "DASHBOARD_CALLBACK": "config.admin_setup.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Бронирования",
                "separator": True,
                "items": [
                    {"title": "Брони", "icon": "event_available", "link": "/admin/bookings/booking/"},
                    {"title": "Платежи Stripe", "icon": "payments", "link": "/admin/payments/payment/"},
                ],
            },
            {
                "title": "Круизы",
                "items": [
                    {"title": "Круизы", "icon": "directions_boat", "link": "/admin/cruises/cruise/"},
                    {"title": "Расписания", "icon": "schedule", "link": "/admin/cruises/cruiseschedule/"},
                    {"title": "Исключения дат", "icon": "event_busy", "link": "/admin/cruises/cruisedateoverride/"},
                ],
            },
            {
                "title": "Контент сайта",
                "items": [
                    {"title": "Статьи блога", "icon": "article", "link": "/admin/cms/blogpost/"},
                    {"title": "Страницы сайта", "icon": "web", "link": "/admin/cms/sitepage/"},
                ],
            },
            {
                "title": "Сайт",
                "items": [
                    {"title": "Статистика", "icon": "insights", "link": "/admin/audit/funnel-dashboard/"},
                ],
            },
            {
                "title": "Коммуникации",
                "items": [
                    {"title": "Email логи", "icon": "mail", "link": "/admin/notifications/emaillog/"},
                    {"title": "SMS логи", "icon": "sms", "link": "/admin/notifications/smslog/"},
                    {"title": "Webhook логи", "icon": "webhook", "link": "/admin/payments/webhooklog/"},
                ],
            },
            {
                "title": "Настройки",
                "items": [
                    {"title": "Users", "icon": "admin_panel_settings", "link": "/admin/auth/user/"},
                ],
            },
        ],
    },
}


def environment_callback(request):
    return [env("DJANGO_ENV", "local"), "primary"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.frontend.middleware.LocalePrefixMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.ApiLoggingMiddleware",
    "apps.audit.page_middleware.PageLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.frontend.context_processors.booking_config",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    if parsed.scheme == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": parsed.path}
    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


DATABASE_URL = env("DATABASE_URL")
DATABASES = {
    "default": database_from_url(DATABASE_URL)
    if DATABASE_URL
    else {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Asia/Nicosia"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser", "rest_framework.parsers.FormParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Turtle Cruise Cyprus API",
    "DESCRIPTION": "Booking, payments, notifications and audit API for turtlecruisecyprus.com Django backend.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "expire-stale-pending-bookings": {
        "task": "apps.bookings.tasks.expire_stale_pending_bookings",
        "schedule": 1800.0,
    },
    "retry-failed-notifications": {
        "task": "apps.notifications.tasks.retry_failed_notifications",
        "schedule": 300.0,
    },
    "mark-abandoned-sessions": {
        "task": "apps.audit.tasks.mark_abandoned_sessions",
        "schedule": 900.0,
    },
    "finalize-stale-page-views": {
        "task": "apps.audit.tasks.finalize_stale_page_views",
        "schedule": 600.0,
    },
}

BOOKING_OVERBOOK_TOLERANCE = int(env("BOOKING_OVERBOOK_TOLERANCE", "1"))
SITE_BASE_URL = env("SITE_BASE_URL", "http://localhost:8000")
GTM_CONTAINER_ID = env("GTM_CONTAINER_ID", "GTM-K63GCMLB")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", "book@turtlecruisecyprus.com")
SUPPORT_PHONE = env("SUPPORT_PHONE")
MEETING_POINT = env("MEETING_POINT", "Ayia Napa Harbour (Limanaki)")

STRIPE_MODE = env("STRIPE_MODE", "test")
if STRIPE_MODE == "test":
    STRIPE_PUBLIC_KEY = (
        env("STRIPE_TEST_PUBLIC_KEY")
        or env("PHP_CONSTANT_TC_STRIPE_PUBLIC_KEY_2")
        or env("STRIPE_PUBLIC_KEY")
        or env("PHP_CONSTANT_TC_STRIPE_PUBLIC_KEY")
    )
    STRIPE_SECRET_KEY = (
        env("STRIPE_TEST_SECRET_KEY")
        or env("PHP_CONSTANT_TC_STRIPE_SECRET_KEY_2")
        or env("STRIPE_SECRET_KEY")
        or env("PHP_CONSTANT_TC_STRIPE_SECRET_KEY")
    )
else:
    STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY") or env("PHP_CONSTANT_TC_STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY") or env("PHP_CONSTANT_TC_STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET") or env("WP_OPTION_MPA_STRIPE_PAYMENT_GATEWAY_WEBHOOK_KEY")

BREVO_API_KEY = env("BREVO_API_KEY")
BREVO_SMTP_HOST = env("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
BREVO_SMTP_PORT = int(env("BREVO_SMTP_PORT", "587"))
BREVO_SMTP_USERNAME = env("BREVO_SMTP_USERNAME") or env("WP_OPTION_MAILSERVER_LOGIN")
BREVO_SMTP_PASSWORD = env("BREVO_SMTP_PASSWORD") or env("WP_OPTION_MAILSERVER_PASS")
BREVO_SENDER_EMAIL = env("BREVO_SENDER_EMAIL", "book@turtlecruisecyprus.com")
BREVO_SENDER_NAME = env("BREVO_SENDER_NAME", "Turtle Cruise Cyprus")
ADMIN_EMAIL_RECIPIENTS = env_list("ADMIN_EMAIL_RECIPIENTS", "book@turtlecruisecyprus.com")

CLICKSEND_USERNAME = env("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = env("CLICKSEND_API_KEY")
CLICKSEND_SENDER_ID = env("CLICKSEND_SENDER_ID")
ADMIN_SMS_RECIPIENTS = env_list("ADMIN_SMS_RECIPIENTS")

# Admin instant alerts: sms (ClickSend, default), telegram, both, none
ADMIN_NOTIFY_CHANNEL = env("ADMIN_NOTIFY_CHANNEL", "sms")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_CHAT_IDS = env_list("TELEGRAM_ADMIN_CHAT_IDS")

WP_SQL_DUMP_PATH = env(
    "WP_SQL_DUMP_PATH",
    str(REPO_DIR / "turtlecruisebyscubacat/dup-installer/dup-database__46e869c-06090919.sql"),
)
