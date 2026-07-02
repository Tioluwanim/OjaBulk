"""
core/config.py

Centralizes all environment variable loading and validation.
Every other file should import settings from here instead of
calling os.getenv() directly — this is the single source of truth
for configuration and makes missing-env-var errors surface at
startup instead of deep inside a random request.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Nomba ────────────────────────────────────────────────────────────
    NOMBA_BASE_URL       = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com/v1")
    NOMBA_ACCOUNT_ID     = os.getenv("NOMBA_ACCOUNT_ID")
    NOMBA_CLIENT_ID      = os.getenv("NOMBA_CLIENT_ID")
    NOMBA_CLIENT_SECRET  = os.getenv("NOMBA_CLIENT_SECRET")
    NOMBA_WEBHOOK_SECRET = os.getenv("NOMBA_WEBHOOK_SECRET")

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://ojabulk:ojabulk@localhost:5432/ojabulk"
    )

    # ── SMS ──────────────────────────────────────────────────────────────
    TERMII_API_KEY = os.getenv("TERMII_API_KEY", "")
    SMS_SENDER_ID  = os.getenv("SMS_SENDER_ID", "OjaBulk")

    # ── USSD ─────────────────────────────────────────────────────────────
    AFRICAS_TALKING_API_KEY   = os.getenv("AFRICAS_TALKING_API_KEY", "")
    AFRICAS_TALKING_USERNAME  = os.getenv("AFRICAS_TALKING_USERNAME", "")

    # ── Deployment ───────────────────────────────────────────────────────
    RENDER_APP_URL = os.getenv("RENDER_APP_URL", "")
    ENVIRONMENT    = os.getenv("ENVIRONMENT", "development")

    @classmethod
    def validate(cls):
        """
        Call this once at startup (in main.py lifespan) to fail fast
        if required config is missing, rather than discovering it
        mid-demo when a webhook fires and crashes.
        """
        required = {
            "NOMBA_ACCOUNT_ID":     cls.NOMBA_ACCOUNT_ID,
            "NOMBA_CLIENT_ID":      cls.NOMBA_CLIENT_ID,
            "NOMBA_CLIENT_SECRET":  cls.NOMBA_CLIENT_SECRET,
            "NOMBA_WEBHOOK_SECRET": cls.NOMBA_WEBHOOK_SECRET,
            "DATABASE_URL":         cls.DATABASE_URL,
        }
        missing = [key for key, val in required.items() if not val]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Check your .env file or Render environment settings."
            )


settings = Settings()