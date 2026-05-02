"""Newsletter builder tools for Parlant."""

import logging
from typing import List, Optional

import parlant.sdk as p

from app.services.newsletter_builder_service import NewsletterBuilderService
from app.services.newsletter_defaults import (
    DEFAULT_NEWSLETTER_THEMES,
    MAX_NEWSLETTER_THEMES,
)
from app.services.newsletter_service import NewsletterService
from app.services.resend_service import ResendService

logger = logging.getLogger(__name__)


def create_newsletter_tools(
    newsletter_service: NewsletterService,
    newsletter_builder_service: NewsletterBuilderService,
):
    """Create newsletter builder tools."""

    def _resolve_user_id(
        context: p.ToolContext, provided_user_id: Optional[str] = None
    ) -> Optional[str]:
        if provided_user_id:
            return provided_user_id

        plugin_data = getattr(context, "plugin_data", {}) or {}
        for key in ("user_id", "supabase_user_id", "customer_id"):
            value = plugin_data.get(key)
            if value:
                return str(value)

        customer = getattr(context, "customer", None)
        if customer:
            metadata = getattr(customer, "metadata", None) or {}
            if isinstance(metadata, dict):
                for key in ("user_id", "supabase_user_id"):
                    value = metadata.get(key)
                    if value:
                        return str(value)

        session = getattr(context, "session", None)
        session_customer = getattr(session, "customer", None) if session else None
        if session_customer:
            metadata = getattr(session_customer, "metadata", None) or {}
            if isinstance(metadata, dict):
                for key in ("user_id", "supabase_user_id"):
                    value = metadata.get(key)
                    if value:
                        return str(value)

        if getattr(context, "customer_id", None):
            return str(context.customer_id)
        return None

    def _resolve_email(
        context: p.ToolContext, provided_email: Optional[str] = None
    ) -> Optional[str]:
        if provided_email:
            return provided_email

        plugin_data = getattr(context, "plugin_data", {}) or {}
        for key in ("email", "user_email", "customer_email"):
            value = plugin_data.get(key)
            if value:
                return str(value)

        customer = getattr(context, "customer", None)
        if customer:
            direct_email = getattr(customer, "email", None)
            if direct_email:
                return str(direct_email)
            metadata = getattr(customer, "metadata", None) or {}
            if isinstance(metadata, dict):
                for key in ("email", "user_email", "customer_email"):
                    value = metadata.get(key)
                    if value:
                        return str(value)

        session = getattr(context, "session", None)
        session_customer = getattr(session, "customer", None) if session else None
        if session_customer:
            direct_email = getattr(session_customer, "email", None)
            if direct_email:
                return str(direct_email)
            metadata = getattr(session_customer, "metadata", None) or {}
            if isinstance(metadata, dict):
                for key in ("email", "user_email", "customer_email"):
                    value = metadata.get(key)
                    if value:
                        return str(value)
        return None

    @p.tool
    async def list_newsletters(
        context: p.ToolContext, user_id: Optional[str] = None
    ) -> p.ToolResult:
        """List all newsletters for a user."""
        try:
            resolved_user_id = _resolve_user_id(context, user_id)
            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )

            newsletters = newsletter_service.list_newsletters(user_id=resolved_user_id)
            return p.ToolResult(
                data={
                    "newsletters": newsletters,
                    "count": len(newsletters),
                    "default_themes": DEFAULT_NEWSLETTER_THEMES,
                }
            )
        except Exception as exc:
            logger.error("Failed to list newsletters: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to list newsletters: {exc}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def create_newsletter(
        context: p.ToolContext,
        title: str,
        themes: List[str],
        frequency_type: str = "daily",
        frequency_interval_days: int = 1,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> p.ToolResult:
        """Create a user newsletter builder profile with max 5 themes.

        frequency_type options: daily, weekly, every_n_days.
        """
        try:
            safe_title = (title or "").strip()
            if not safe_title:
                return p.ToolResult(
                    data=(
                        "Please provide a title for your newsletter so I can create it."
                    ),
                    control={"lifespan": "response"},
                )

            resolved_user_id = _resolve_user_id(context, user_id)
            resolved_email = _resolve_email(context, email)

            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )
            if not resolved_email:
                return p.ToolResult(
                    data=(
                        "I could not find your email in session context. "
                        "Please provide the email address for newsletter delivery."
                    ),
                    control={"lifespan": "response"},
                )

            selected_themes = themes or DEFAULT_NEWSLETTER_THEMES

            if len(selected_themes) > MAX_NEWSLETTER_THEMES:
                return p.ToolResult(
                    data=(
                        f"You can define at most {MAX_NEWSLETTER_THEMES} themes. "
                        f"Defaults available: {', '.join(DEFAULT_NEWSLETTER_THEMES)}."
                    ),
                    control={"lifespan": "response"},
                )

            newsletter = newsletter_service.create_newsletter(
                user_id=resolved_user_id,
                email=resolved_email,
                title=safe_title,
                themes=selected_themes,
                frequency_type=frequency_type,
                frequency_interval_days=frequency_interval_days,
            )
            return p.ToolResult(
                data={
                    "message": "Newsletter created successfully.",
                    "applied_themes": selected_themes,
                    "newsletter": newsletter,
                }
            )
        except Exception as exc:
            logger.error("Failed to create newsletter: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to create newsletter: {exc}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def update_newsletter(
        context: p.ToolContext,
        newsletter_id: int,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        themes_csv: Optional[str] = None,
        email: Optional[str] = None,
        frequency_type: Optional[str] = None,
        frequency_interval_days: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> p.ToolResult:
        """Update newsletter title/themes/email/schedule.

        themes_csv format example: "videogames, tecnologia, esportes"
        """
        try:
            resolved_user_id = _resolve_user_id(context, user_id)
            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )

            resolved_email = _resolve_email(context, email) if email is not None else None
            parsed_themes: Optional[List[str]] = None
            if themes_csv is not None:
                parsed_themes = [item.strip() for item in themes_csv.split(",")]

            updated = newsletter_service.update_newsletter(
                newsletter_id=newsletter_id,
                user_id=resolved_user_id,
                title=title,
                themes=parsed_themes,
                email=resolved_email,
                frequency_type=frequency_type,
                frequency_interval_days=frequency_interval_days,
                is_active=is_active,
            )
            if not updated:
                return p.ToolResult(
                    data=f"No newsletter found with ID {newsletter_id} for this user.",
                    control={"lifespan": "response"},
                )
            return p.ToolResult(
                data={
                    "message": "Newsletter updated successfully.",
                    "newsletter": updated,
                }
            )
        except Exception as exc:
            logger.error("Failed to update newsletter: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to update newsletter: {exc}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def delete_newsletter(
        context: p.ToolContext,
        newsletter_id: int,
        user_id: Optional[str] = None,
    ) -> p.ToolResult:
        """Delete newsletter by id."""
        try:
            resolved_user_id = _resolve_user_id(context, user_id)
            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )

            deleted = newsletter_service.delete_newsletter(
                newsletter_id=newsletter_id, user_id=resolved_user_id
            )
            if not deleted:
                return p.ToolResult(
                    data=f"No newsletter found with ID {newsletter_id} for this user.",
                    control={"lifespan": "response"},
                )
            return p.ToolResult(
                data=f"Newsletter ID {newsletter_id} deleted successfully."
            )
        except Exception as exc:
            logger.error("Failed to delete newsletter: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to delete newsletter: {exc}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def generate_newsletter_content(
        context: p.ToolContext,
        newsletter_id: int,
        user_id: Optional[str] = None,
        language: str = "pt-BR",
    ) -> p.ToolResult:
        """Generate newsletter content with Agno and save it."""
        try:
            resolved_user_id = _resolve_user_id(context, user_id)
            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )

            newsletter = newsletter_service.get_newsletter(newsletter_id, resolved_user_id)
            if not newsletter:
                return p.ToolResult(
                    data=f"No newsletter found with ID {newsletter_id} for this user.",
                    control={"lifespan": "response"},
                )

            draft = newsletter_builder_service.build_newsletter(
                title=newsletter["title"],
                themes=newsletter["themes"],
                language=language,
            )
            updated = newsletter_service.save_generated_content(
                newsletter_id=newsletter_id,
                title=draft.title,
                html_content=draft.html_content,
                text_content=draft.text_content,
            )
            return p.ToolResult(
                data={
                    "message": "Newsletter content generated successfully.",
                    "newsletter": updated,
                }
            )
        except Exception as exc:
            logger.error("Failed to generate newsletter content: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to generate newsletter content: {exc}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def send_newsletter_now(
        context: p.ToolContext,
        newsletter_id: int,
        user_id: Optional[str] = None,
    ) -> p.ToolResult:
        """Generate if needed and send newsletter email immediately using Resend."""
        try:
            resolved_user_id = _resolve_user_id(context, user_id)
            if not resolved_user_id:
                return p.ToolResult(
                    data=(
                        "I could not identify your user account from session context. "
                        "Please provide your user_id."
                    ),
                    control={"lifespan": "response"},
                )

            newsletter = newsletter_service.get_newsletter(newsletter_id, resolved_user_id)
            if not newsletter:
                return p.ToolResult(
                    data=f"No newsletter found with ID {newsletter_id} for this user.",
                    control={"lifespan": "response"},
                )

            html_content = newsletter.get("generated_html_content")
            text_content = newsletter.get("generated_text_content")
            subject = newsletter.get("generated_title") or newsletter["title"]

            if not html_content or not text_content:
                draft = newsletter_builder_service.build_newsletter(
                    title=newsletter["title"], themes=newsletter["themes"]
                )
                html_content = draft.html_content
                text_content = draft.text_content
                subject = draft.title
                newsletter_service.save_generated_content(
                    newsletter_id=newsletter_id,
                    title=subject,
                    html_content=html_content,
                    text_content=text_content,
                )

            resend_service = ResendService()
            provider_message_id = await resend_service.send_newsletter(
                to_email=newsletter["email"],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
            newsletter_service.register_delivery(
                newsletter_id=newsletter_id, provider_message_id=provider_message_id
            )

            return p.ToolResult(
                data={
                    "message": "Newsletter sent successfully.",
                    "provider_message_id": provider_message_id,
                }
            )
        except Exception as exc:
            logger.error("Failed to send newsletter now: %s", exc, exc_info=True)
            return p.ToolResult(
                data=f"Failed to send newsletter now: {exc}",
                control={"lifespan": "response"},
            )

    return [
        list_newsletters,
        create_newsletter,
        update_newsletter,
        delete_newsletter,
        generate_newsletter_content,
        send_newsletter_now,
    ]
