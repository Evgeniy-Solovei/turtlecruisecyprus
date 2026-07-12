from __future__ import annotations

import requests
from django.conf import settings


class TelegramNotConfigured(RuntimeError):
    pass


def send_telegram_message(*, chat_id: str, text: str) -> str:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramNotConfigured("TELEGRAM_BOT_TOKEN is not configured.")
    response = requests.post(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get("result", {}).get("message_id", ""))
