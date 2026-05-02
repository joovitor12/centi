"""Application settings and environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""

    # Supabase
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

    # OpenAI (used by Parlant)
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    AGNO_MODEL_ID: str = os.environ.get("AGNO_MODEL_ID", "gpt-5.4-mini")

    # Langfuse
    LANGFUSE_SECRET_KEY: str = os.environ.get("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_BASE_URL: str = os.environ.get("LANGFUSE_BASE_URL", "")

    # Resend
    RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.environ.get("RESEND_FROM_EMAIL", "")

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        required = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_KEY": cls.SUPABASE_KEY,
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


settings = Settings()
