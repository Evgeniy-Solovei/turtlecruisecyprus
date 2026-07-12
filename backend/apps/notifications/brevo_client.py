from __future__ import annotations

import smtplib
from email.message import EmailMessage

import requests
from django.conf import settings


class BrevoNotConfigured(RuntimeError):
    pass


def send_transactional_email(*, to_email: str, subject: str, html: str, text: str = "") -> str:
    if settings.BREVO_API_KEY:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
            json={
                "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html,
                "textContent": text or subject,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("messageId", "")

    if not settings.BREVO_SMTP_USERNAME or not settings.BREVO_SMTP_PASSWORD:
        raise BrevoNotConfigured("Brevo API key or SMTP credentials are not configured.")

    message = EmailMessage()
    message["From"] = f"{settings.BREVO_SENDER_NAME} <{settings.BREVO_SENDER_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text or subject)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.BREVO_SMTP_HOST, settings.BREVO_SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.BREVO_SMTP_USERNAME, settings.BREVO_SMTP_PASSWORD)
        smtp.send_message(message)
    return ""
