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
    NOMBA_BASE_URL_V2    = os.getenv("NOMBA_BASE_URL_V2", "https://sandbox.nomba.com/v2")
    NOMBA_ACCOUNT_ID     = os.getenv("NOMBA_ACCOUNT_ID")
    NOMBA_SUB_ACCOUNT_ID = os.getenv("NOMBA_SUB_ACCOUNT_ID")
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

    # ── Auth (Identity / OTP session tokens) ────────────────────────────
    # Used to sign session tokens issued after OTP verification for
    # traders, heads of traders, and wholesalers. Falls back to a
    # dev-only default so local testing never crashes on a missing
    # key — but a real value MUST be set before Sunday's deploy, since
    # anyone who knows the dev default could forge a valid session
    # token against your live Render instance.
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-default-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))

    # Simple hardcoded admin key — gates POST /identities (creating
    # head_of_traders and wholesaler logins). This is deliberately NOT
    # a full admin role inside the Identity system — that would be a
    # much bigger feature than a hackathon needs. This is the same
    # lightweight "one API key" approach discussed earlier in the
    # project for protecting admin-only actions.
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-only-admin-key-change-me")

    @classmethod
    def validate(cls):
        """
        Call this once at startup (in main.py lifespan) to fail fast
        if required config is missing, rather than discovering it
        mid-demo when a webhook fires and crashes.
        """
        required = {
            "NOMBA_ACCOUNT_ID":     cls.NOMBA_ACCOUNT_ID,
            "NOMBA_SUB_ACCOUNT_ID": cls.NOMBA_SUB_ACCOUNT_ID,
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

        if cls.JWT_SECRET == "dev-only-insecure-default-change-me":
            print(
                "[Settings] WARNING: JWT_SECRET is using the insecure dev "
                "default. Set a real JWT_SECRET in your .env before "
                "deploying to Render, or anyone can forge a valid login "
                "session token."
            )

        if cls.ADMIN_API_KEY == "dev-only-admin-key-change-me":
            print(
                "[Settings] WARNING: ADMIN_API_KEY is using the insecure "
                "dev default. Set a real ADMIN_API_KEY before deploying, "
                "or anyone can create fake head_of_traders/wholesaler logins."
            )


settings = Settings()
