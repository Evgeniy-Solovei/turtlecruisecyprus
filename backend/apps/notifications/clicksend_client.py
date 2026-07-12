from __future__ import annotations

import requests
from django.conf import settings


class ClickSendNotConfigured(RuntimeError):
    pass


def send_sms(*, to_phone: str, body: str) -> str:
    if not settings.CLICKSEND_USERNAME or not settings.CLICKSEND_API_KEY:
        raise ClickSendNotConfigured("ClickSend credentials are not configured.")
    response = requests.post(
        "https://rest.clicksend.com/v3/sms/send",
        auth=(settings.CLICKSEND_USERNAME, settings.CLICKSEND_API_KEY),
        json={"messages": [{"to": to_phone, "body": body, "source": "django", "from": settings.CLICKSEND_SENDER_ID or None}]},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    messages = data.get("data", {}).get("messages", [])
    return messages[0].get("message_id", "") if messages else ""
