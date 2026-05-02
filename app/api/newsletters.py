"""FastAPI routes for newsletter builder management."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.newsletter_builder_service import NewsletterBuilderService
from app.services.newsletter_service import NewsletterService
from app.services.resend_service import ResendService
from app.services.supabase_service import SupabaseService

router = APIRouter(prefix="/newsletters", tags=["newsletters"])

supabase_service = SupabaseService()
newsletter_service = NewsletterService(supabase_service=supabase_service)
builder_service = NewsletterBuilderService()


class CreateNewsletterRequest(BaseModel):
    user_id: str
    email: str
    title: str
    themes: List[str] = Field(default_factory=list)
    frequency_type: str = "daily"
    frequency_interval_days: int = 1


class UpdateNewsletterRequest(BaseModel):
    title: Optional[str] = None
    themes: Optional[List[str]] = None
    email: Optional[str] = None
    frequency_type: Optional[str] = None
    frequency_interval_days: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("")
def list_newsletters(user_id: str):
    return {"newsletters": newsletter_service.list_newsletters(user_id=user_id)}


@router.post("")
def create_newsletter(payload: CreateNewsletterRequest):
    try:
        return newsletter_service.create_newsletter(
            user_id=payload.user_id,
            email=payload.email,
            title=payload.title,
            themes=payload.themes,
            frequency_type=payload.frequency_type,
            frequency_interval_days=payload.frequency_interval_days,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{newsletter_id}")
def update_newsletter(newsletter_id: int, user_id: str, payload: UpdateNewsletterRequest):
    updated = newsletter_service.update_newsletter(
        newsletter_id=newsletter_id,
        user_id=user_id,
        title=payload.title,
        themes=payload.themes,
        email=payload.email,
        frequency_type=payload.frequency_type,
        frequency_interval_days=payload.frequency_interval_days,
        is_active=payload.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Newsletter not found.")
    return updated


@router.delete("/{newsletter_id}")
def delete_newsletter(newsletter_id: int, user_id: str):
    deleted = newsletter_service.delete_newsletter(
        newsletter_id=newsletter_id,
        user_id=user_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Newsletter not found.")
    return {"ok": True}


@router.post("/{newsletter_id}/generate")
def generate_newsletter(newsletter_id: int, user_id: str, language: str = "pt-BR"):
    newsletter = newsletter_service.get_newsletter(newsletter_id, user_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found.")

    draft = builder_service.build_newsletter(
        title=newsletter["title"],
        themes=newsletter["themes"],
        language=language,
    )
    return newsletter_service.save_generated_content(
        newsletter_id=newsletter_id,
        title=draft.title,
        html_content=draft.html_content,
        text_content=draft.text_content,
    )


@router.post("/{newsletter_id}/send")
async def send_newsletter(newsletter_id: int, user_id: str):
    newsletter = newsletter_service.get_newsletter(newsletter_id, user_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found.")

    html_content = newsletter.get("generated_html_content")
    text_content = newsletter.get("generated_text_content")
    subject = newsletter.get("generated_title") or newsletter["title"]

    if not html_content or not text_content:
        draft = builder_service.build_newsletter(
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
        newsletter_id=newsletter_id,
        provider_message_id=provider_message_id,
    )
    return {"ok": True, "provider_message_id": provider_message_id}
