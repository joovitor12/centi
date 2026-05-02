"""Email sending service using Resend."""

import logging
from typing import Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class ResendService:
    """Service for sending transactional emails with Resend."""

    API_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        if not settings.RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is required to send newsletter emails.")
        if not settings.RESEND_FROM_EMAIL:
            raise ValueError(
                "RESEND_FROM_EMAIL is required to send newsletter emails."
            )

    async def send_newsletter(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> str:
        """Send an email and return the provider message id."""
        payload = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        if text_content:
            payload["text"] = text_content

        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.API_URL, json=payload, headers=headers)
            if response.status_code >= 300:
                logger.error(
                    "Resend send failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise RuntimeError(
                    f"Resend send failed with status {response.status_code}"
                )
            data = response.json()
            return str(data.get("id", ""))
