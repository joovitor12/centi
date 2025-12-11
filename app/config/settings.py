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

    # Google Calendar
    GOOGLE_CREDENTIALS_PATH: str = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    GOOGLE_CREDENTIALS_JSON: str = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")  # JSON string for cloud deployments
    GOOGLE_TOKEN_PATH: str = os.environ.get("GOOGLE_TOKEN_PATH", "")
    GOOGLE_TOKEN_JSON: str = os.environ.get("GOOGLE_TOKEN_JSON", "")  # JSON string for cloud deployments
    GOOGLE_CALENDAR_ID: str = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    GOOGLE_CALENDAR_TIMEZONE: str = os.environ.get(
        "GOOGLE_CALENDAR_TIMEZONE", "America/Sao_Paulo"
    )
    
    # OAuth for multi-user onboarding
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")

    # Gmail
    GMAIL_POLL_INTERVAL_SECONDS: int = os.environ.get("GMAIL_POLL_INTERVAL_SECONDS", 120)
    CENTI_EMAIL_ADDRESS: str = os.environ.get("CENTI_EMAIL_ADDRESS", "")

    # Langfuse
    LANGFUSE_SECRET_KEY: str = os.environ.get("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_BASE_URL: str = os.environ.get("LANGFUSE_BASE_URL", "")
    
    # Parlant
    PARLANT_SERVER_URL: str = os.environ.get("PARLANT_SERVER_URL", "http://localhost:8800")
    PARLANT_AGENT_ID: str = os.environ.get("PARLANT_AGENT_ID", "")

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
