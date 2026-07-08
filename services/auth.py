"""
services/auth.py

OTP-based login for all three OjaBulk roles: trader, head_of_traders,
wholesaler. Same flow for all three — only what the resulting session
token is ALLOWED to do differs (enforced in routers, not here).

Flow:
    1. request_otp(phone) -> generates a 6-digit code, stores an
       OTPSession row, sends it via SMS. Returns nothing sensitive.
    2. verify_otp(phone, code) -> checks the code is valid, unused,
       and not expired. If valid, marks it used and issues a JWT
       session token containing the Identity's id, role, and
       market_name (for head_of_traders scoping).
    3. get_current_identity (FastAPI dependency) -> decodes the JWT
       from the Authorization header, loads the Identity from DB,
       and makes it available to any route via Depends().
    4. require_role(...) -> a dependency factory that wraps
       get_current_identity and raises 403 if the identity's role
       doesn't match what the route requires.

SECURITY NOTE ON OTP CODE GENERATION:
    Uses Python's `secrets` module, not `random`. `random` is not
    cryptographically secure and must never be used to generate any
    code that gates access to an account — an attacker who can
    predict or narrow down the random seed could guess valid OTP
    codes. `secrets.randbelow()` is the correct tool here.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models import Identity, IdentityRole, OTPSession
from services.sms import sms_service


class OTPRequestError(Exception):
    """Raised when an OTP cannot be requested (e.g. unknown phone)."""
    pass


class OTPVerificationError(Exception):
    """Raised when an OTP code is invalid, expired, or already used."""
    pass


def _generate_otp_code() -> str:
    """
    Generates a cryptographically secure 6-digit numeric code.
    NEVER use the `random` module here — see module docstring.
    """
    return str(secrets.randbelow(1_000_000)).zfill(6)


def request_otp(db: Session, phone: str) -> None:
    """
    Generates and sends an OTP code to the given phone number.

    Does NOT reveal whether the phone number is registered — the SMS
    is only actually sent if an Identity with this phone exists, but
    the function returns the same way either way, so this endpoint
    can't be used to enumerate which phone numbers are registered
    identities on the platform.

    Args:
        db:    Database session
        phone: Phone number in canonical 0XXXXXXXXXX format (same
               normalization TraderCreate already enforces)

    Raises:
        Nothing — always returns None, by design (see above)
    """
    identity = db.query(Identity).filter(
        Identity.phone == phone
    ).first()

    if not identity:
        # Deliberately silent — do not reveal phone is unregistered
        return

    # ── DEMO INTERCEPTION ────────────────────────────────────────────────
    # Check if this phone number is registered as a demo/judge account
    if phone in settings.DEMO_PHONE_NUMBERS:
        code = settings.DEMO_OTP_CODE
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )

        otp_session = OTPSession(
            id=uuid.uuid4(),
            phone=phone,
            code=code,
            expires_at=expires_at,
            used=False,
        )
        db.add(otp_session)
        db.commit()
        
        print(f"[Auth] Demo account intercept for {phone} -- Using fixed OTP: {code}")
        return  # Exit early so we don't generate a random code or send an SMS
    # ─────────────────────────────────────────────────────────────────────

    # Normal flow for real users
    code = _generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OTP_EXPIRY_MINUTES
    )

    otp_session = OTPSession(
        id=uuid.uuid4(),
        phone=phone,
        code=code,
        expires_at=expires_at,
        used=False,
    )
    db.add(otp_session)
    db.commit()

    sent = sms_service.send_otp_code(phone=phone, code=code)

    if not sent:
        # SMS delivery failed (provider down, sender ID not approved,
        # etc). Log the code itself so it's still retrievable from
        # Render's logs during a demo/testing -- otherwise a trader is
        # completely locked out with no way to get their code.
        # NOTE: this is a deliberate, temporary safety net for
        # demo/hackathon use. In a real production deployment with
        # live traders, printing OTPs to logs is a security risk
        # (anyone with log access can log in as any trader) -- remove
        # or gate this behind an environment check once SMS delivery
        # is reliable.
        print(
            f"[Auth] SMS send failed for {phone} -- "
            f"OTP CODE: {code} (expires {expires_at.isoformat()})"
        )


def verify_otp(db: Session, phone: str, code: str) -> dict:
    """
    Verifies an OTP code and, if valid, issues a session token.

    Args:
        db:    Database session
        phone: Phone number the code was sent to
        code:  The 6-digit code the user submitted

    Returns:
        {
            "access_token": str,
            "role":         str,
            "display_name": str,
            "market_name":  str | None,
        }

    Raises:
        OTPVerificationError: If the code is invalid, expired, or
                              already used
    """
    otp_session = db.query(OTPSession).filter(
        OTPSession.phone == phone,
        OTPSession.code == code,
        OTPSession.used == False,  # noqa: E712 — SQLAlchemy requires == here
    ).order_by(OTPSession.created_at.desc()).first()

    if not otp_session:
        raise OTPVerificationError(
            "Invalid or already-used OTP code."
        )

    now = datetime.now(timezone.utc)
    expires_at = otp_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        raise OTPVerificationError(
            "OTP code has expired. Request a new one."
        )

    otp_session.used = True

    identity = db.query(Identity).filter(
        Identity.phone == phone
    ).first()

    if not identity:
        # Should not happen if request_otp's silent-skip is working
        # correctly, but defended against anyway.
        raise OTPVerificationError(
            "No identity found for this phone number."
        )

    db.commit()

    access_token = _issue_token(identity)

    return {
        "access_token": access_token,
        "role":         identity.role.value,
        "display_name": identity.display_name,
        "market_name":  identity.market_name,
    }


def _issue_token(identity: Identity) -> str:
    """
    Issues a signed JWT containing exactly what routers need to
    enforce role + market scoping, without a database lookup on
    every single request. (get_current_identity below still does
    look the Identity up fresh each time, to catch role changes or
    deactivation immediately — the JWT is proof of WHO, the DB
    lookup confirms they still SHOULD be allowed in.)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "identity_id": str(identity.id),
        "phone":       identity.phone,
        "role":        identity.role.value,
        "market_name": identity.market_name,
        "iat":         now,
        "exp":         now + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid session token."
        )


def get_current_identity(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> Identity:
    """
    FastAPI dependency. Decodes the Bearer token from the Authorization
    header, re-fetches the Identity from the database fresh (not just
    trusting the JWT payload), and returns it.

    Usage:
        @router.get("/me")
        def me(identity: Identity = Depends(get_current_identity)):
            ...
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or malformed Authorization header. "
                   "Expected: Bearer <token>"
        )

    token = authorization[len("Bearer "):]
    payload = _decode_token(token)

    try:
        identity_uuid = uuid.UUID(payload["identity_id"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Malformed session token."
        )

    identity = db.query(Identity).filter(
        Identity.id == identity_uuid
    ).first()

    if not identity:
        raise HTTPException(
            status_code=401,
            detail="Identity no longer exists."
        )

    return identity


def get_current_identity_optional(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> Identity | None:
    """
    Same as get_current_identity, but returns None instead of raising
    401 when no Authorization header is present at all — for routes
    that are PUBLIC by default but behave differently when a caller
    happens to be logged in (e.g. GET /pools, which is open to
    everyone, but supports an authenticated ?supplier=me filter for
    wholesaler on top of the same public route).

    A malformed or expired token still raises 401 here, same as the
    non-optional version — "no token" and "bad token" are different
    situations. Silently treating a bad token as "not logged in"
    would hide real problems (e.g. an expired session) behind a
    confusing empty result instead of a clear error.
    """
    if not authorization:
        return None
    return get_current_identity(authorization=authorization, db=db)


def require_role(*allowed_roles: IdentityRole):
    """
    Dependency factory — returns a FastAPI dependency that only allows
    identities with one of the given roles through, and 403s otherwise.

    Usage:
        @router.post("/pools")
        def create_pool(
            identity: Identity = Depends(
                require_role(IdentityRole.HEAD_OF_TRADERS)
            ),
            ...
        ):
            ...

    IMPORTANT: this checks ROLE only. Market-scoping (a Head of
    Traders can only create pools for their own market_name) is a
    SEPARATE check that must still happen inside the route itself,
    comparing identity.market_name against the pool being created —
    this dependency has no knowledge of what the request body contains.
    """
    def dependency(
        identity: Identity = Depends(get_current_identity),
    ) -> Identity:
        if identity.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"This action requires role "
                    f"{' or '.join(r.value for r in allowed_roles)}, "
                    f"but you are logged in as {identity.role.value}."
                )
            )
        return identity

    return dependency
