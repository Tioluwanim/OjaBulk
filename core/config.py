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
    # SMS_PROVIDER picks which provider services/sms.py actually calls.
    # "arkesel" is the primary choice (see services/sms.py's module
    # docstring for why). "termii" is kept wired as a same-day fallback —
    # if Arkesel has any issue (sender-ID approval delay, unexpected
    # payload quirk, rate limiting) before the demo, set
    # SMS_PROVIDER=termii and everything works again with zero code
    # changes, since Termii credentials were never removed.
    SMS_PROVIDER   = os.getenv("SMS_PROVIDER", "arkesel").strip().lower()
    SMS_SENDER_ID  = os.getenv("SMS_SENDER_ID", "OjaBulk")

    ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "")

    TERMII_API_KEY = os.getenv("TERMII_API_KEY", "")

    GIDEONS_SMS_API_KEY = os.getenv("GIDEONS_SMS_API_KEY", "")

    SENDCHAMP_API_KEY = os.getenv("SENDCHAMP_API_KEY", "")
    SENDCHAMP_ROUTE = os.getenv("SENDCHAMP_ROUTE", "non_dnd")

    # "sms" (default) sends a text via services/sms.py's active provider.
    # "voice" uses Termii's Voice Token API instead -- a phone CALL that
    # reads out the OTP digits. "twilio_verify" uses Twilio's Verify
    # API -- Twilio generates, delivers (SMS by default), and checks
    # the code itself, offloading that logic entirely instead of
    # OjaBulk's own OTPSession comparison. See services/voice_otp.py
    # and services/twilio_verify.py.
    OTP_DELIVERY_CHANNEL = os.getenv("OTP_DELIVERY_CHANNEL", "sms")

    # Judging/demo accounts: any phone number listed here always gets
    # the SAME fixed OTP code (DEMO_OTP_CODE) instead of a random one,
    # and no SMS/voice delivery is even attempted for it -- so judges
    # can log in reliably without depending on whichever SMS provider
    # is or isn't working that day. Comma-separated, e.g.
    # "2348010000001,2348010000002". Leave empty to disable entirely.
    # SECURITY NOTE: this is a deliberate, temporary bypass for
    # judging purposes. Anyone who knows a demo phone number and the
    # fixed code can log in as that account -- keep the demo list
    # small, use throwaway seeded accounts (not a real trader's own
    # number), and remove these env vars after judging.
    DEMO_PHONE_NUMBERS = [
        p.strip() for p in os.getenv("DEMO_PHONE_NUMBERS", "").split(",") if p.strip()
    ]
    DEMO_OTP_CODE = os.getenv("DEMO_OTP_CODE", "000000")

    TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "")
    TWILIO_FROM_NUMBER  = os.getenv("TWILIO_FROM_NUMBER", "")

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
