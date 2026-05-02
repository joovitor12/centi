"""Background worker that sends scheduled newsletters."""

import asyncio
import logging

from app.config.settings import settings
from app.services.newsletter_builder_service import NewsletterBuilderService
from app.services.newsletter_service import NewsletterService
from app.services.resend_service import ResendService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


async def run_newsletter_worker(poll_interval_seconds: int = 60) -> None:
    """Poll due newsletters, generate content, and deliver by email."""
    settings.validate()
    supabase_service = SupabaseService()
    newsletter_service = NewsletterService(supabase_service=supabase_service)
    builder_service = NewsletterBuilderService()
    resend_service = ResendService()

    logger.info("Newsletter worker started with %s second polling", poll_interval_seconds)

    while True:
        try:
            due_newsletters = newsletter_service.list_due_newsletters()
            logger.info("Found %s due newsletters", len(due_newsletters))

            for newsletter in due_newsletters:
                newsletter_id = int(newsletter["id"])

                draft = builder_service.build_newsletter(
                    title=newsletter["title"],
                    themes=newsletter["themes"],
                )
                newsletter_service.save_generated_content(
                    newsletter_id=newsletter_id,
                    title=draft.title,
                    html_content=draft.html_content,
                    text_content=draft.text_content,
                )

                provider_message_id = await resend_service.send_newsletter(
                    to_email=newsletter["email"],
                    subject=draft.title,
                    html_content=draft.html_content,
                    text_content=draft.text_content,
                )
                newsletter_service.register_delivery(
                    newsletter_id=newsletter_id,
                    provider_message_id=provider_message_id,
                )

            await asyncio.sleep(poll_interval_seconds)
        except Exception as exc:
            logger.error("Newsletter worker loop error: %s", exc, exc_info=True)
            await asyncio.sleep(poll_interval_seconds)
