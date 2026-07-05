"""
models/otp_session.py

Short-lived OTP codes for phone-based login.

Flow:
    1. Identity requests login -> POST /auth/request-otp {phone}
       -> creates an OTPSession row, sends the code via SMS
    2. Identity submits code -> POST /auth/verify-otp {phone, code}
       -> if valid and not expired, mark used=True, issue a session token

An OTPSession row is single-use (used flag) and expires quickly
(default 10 minutes) — this is deliberately NOT a long-lived table.
Old rows can be purged periodically; nothing else references them by FK.
"""

import uuid

from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class OTPSession(Base):
    __tablename__ = "otp_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    phone = Column(
        String,
        nullable=False,
    )

    code = Column(
        String,
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    used = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
