"""Prompts module for Langfuse integration."""

from langfuse import Langfuse
from app.config.settings import settings

# Initialize Langfuse client with settings
_langfuse_client = None


def get_langfuse_client():
    """Get or create Langfuse client instance."""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_BASE_URL if settings.LANGFUSE_BASE_URL else None,
        )
    return _langfuse_client

