"""Newsletter persistence and scheduling operations."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.newsletter_defaults import DEFAULT_NEWSLETTER_THEMES, normalize_themes
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class NewsletterService:
    """CRUD and schedule logic for newsletters."""

    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
        self.client = supabase_service.client

    def create_newsletter(
        self,
        user_id: str,
        email: str,
        title: str,
        themes: List[str],
        frequency_type: str = "daily",
        frequency_interval_days: int = 1,
        is_default: bool = False,
    ) -> Dict[str, Any]:
        normalized_themes = normalize_themes(themes or DEFAULT_NEWSLETTER_THEMES)
        frequency_type = self._sanitize_frequency_type(frequency_type)
        frequency_interval_days = self._sanitize_frequency_interval_days(
            frequency_interval_days
        )
        now = datetime.utcnow()
        next_run_at = self._compute_next_run_at(
            now=now,
            frequency_type=frequency_type,
            frequency_interval_days=frequency_interval_days,
        )
        payload = {
            "user_id": user_id,
            "email": email,
            "title": title,
            "themes": normalized_themes,
            "frequency_type": frequency_type,
            "frequency_interval_days": frequency_interval_days,
            "is_default": is_default,
            "is_active": True,
            "next_run_at": next_run_at.isoformat(),
        }
        response = self.client.table("newsletters").insert(payload).execute()
        return response.data[0] if response.data else {}

    def list_newsletters(self, user_id: str) -> List[Dict[str, Any]]:
        response = (
            self.client.table("newsletters")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        return response.data or []

    def get_newsletter(self, newsletter_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table("newsletters")
            .select("*")
            .eq("id", newsletter_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def update_newsletter(
        self,
        newsletter_id: int,
        user_id: str,
        title: Optional[str] = None,
        themes: Optional[List[str]] = None,
        email: Optional[str] = None,
        frequency_type: Optional[str] = None,
        frequency_interval_days: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
        if title is not None:
            update_data["title"] = title
        if themes is not None:
            update_data["themes"] = normalize_themes(themes)
        if email is not None:
            update_data["email"] = email
        if is_active is not None:
            update_data["is_active"] = is_active
        if frequency_type is not None:
            update_data["frequency_type"] = frequency_type
        if frequency_interval_days is not None:
            update_data["frequency_interval_days"] = frequency_interval_days

        if frequency_type is not None or frequency_interval_days is not None:
            current = self.get_newsletter(newsletter_id, user_id)
            if not current:
                return {}
            next_run_at = self._compute_next_run_at(
                now=datetime.utcnow(),
                frequency_type=update_data.get(
                    "frequency_type", current["frequency_type"]
                ),
                frequency_interval_days=int(
                    update_data.get(
                        "frequency_interval_days", current["frequency_interval_days"]
                    )
                ),
            )
            update_data["next_run_at"] = next_run_at.isoformat()

        response = (
            self.client.table("newsletters")
            .update(update_data)
            .eq("id", newsletter_id)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return self.get_newsletter(newsletter_id, user_id) or {}

    def delete_newsletter(self, newsletter_id: int, user_id: str) -> bool:
        response = (
            self.client.table("newsletters")
            .delete()
            .eq("id", newsletter_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)

    def save_generated_content(
        self, newsletter_id: int, title: str, html_content: str, text_content: str
    ) -> Dict[str, Any]:
        response = (
            self.client.table("newsletters")
            .update(
                {
                    "generated_title": title,
                    "generated_html_content": html_content,
                    "generated_text_content": text_content,
                    "generated_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", newsletter_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    def list_due_newsletters(self) -> List[Dict[str, Any]]:
        now_iso = datetime.utcnow().isoformat()
        response = (
            self.client.table("newsletters")
            .select("*")
            .eq("is_active", True)
            .lte("next_run_at", now_iso)
            .execute()
        )
        return response.data or []

    def register_delivery(
        self,
        newsletter_id: int,
        provider_message_id: str,
    ) -> None:
        now = datetime.utcnow()
        newsletter = (
            self.client.table("newsletters").select("*").eq("id", newsletter_id).execute()
        )
        if not newsletter.data:
            return
        item = newsletter.data[0]
        next_run_at = self._compute_next_run_at(
            now=now,
            frequency_type=item["frequency_type"],
            frequency_interval_days=item["frequency_interval_days"],
        )

        self.client.table("newsletters").update(
            {
                "last_sent_at": now.isoformat(),
                "last_provider_message_id": provider_message_id,
                "next_run_at": next_run_at.isoformat(),
                "updated_at": now.isoformat(),
            }
        ).eq("id", newsletter_id).execute()

    def _compute_next_run_at(
        self,
        now: datetime,
        frequency_type: str,
        frequency_interval_days: int,
    ) -> datetime:
        frequency = self._sanitize_frequency_type(frequency_type)
        interval_days = self._sanitize_frequency_interval_days(frequency_interval_days)
        if frequency == "daily":
            return now + timedelta(days=1)
        if frequency == "weekly":
            return now + timedelta(days=7)
        if frequency == "every_n_days":
            interval = max(1, int(interval_days))
            return now + timedelta(days=interval)
        raise ValueError(
            "Invalid frequency_type. Use one of: daily, weekly, every_n_days."
        )

    def _sanitize_frequency_type(self, frequency_type: Optional[str]) -> str:
        if frequency_type is None:
            return "daily"
        normalized = str(frequency_type).strip().lower()
        if not normalized:
            return "daily"
        return normalized

    def _sanitize_frequency_interval_days(
        self, frequency_interval_days: Optional[int]
    ) -> int:
        if frequency_interval_days is None:
            return 1
        return max(1, int(frequency_interval_days))
