from config.celery import app

from .services import expire_stale_pending_bookings as expire_stale_pending_bookings_service


@app.task(name="apps.bookings.tasks.expire_stale_pending_bookings")
def expire_stale_pending_bookings() -> int:
    return expire_stale_pending_bookings_service()
