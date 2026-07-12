from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# PostgreSQL: set DATABASE_URL in .env (see scripts/migrate-to-postgres.sh).
# SQLite is used only when DATABASE_URL is empty.

# Локально можно без Redis/Celery: письма уйдут синхронно при подтверждении брони.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
