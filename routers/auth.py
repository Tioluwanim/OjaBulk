"""
routers/auth.py

Login endpoints. Same OTP flow for all three roles — trader,
head_of_traders, wholesaler. What differs between roles is enforced
downstream in other routers (require_role), not here.

ALSO contains POST /identities — the admin-only endpoint that creates
head_of_traders and wholesaler login identities. Trader identities are
NOT created here — they're auto-created at POST /traders registration
time (see routers/traders.py), since a trader identity is always
paired 1:1 with a Trader row and shouldn't be creatable independently
of one.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.identity import Identity, IdentityRole
from services.auth import request_otp, verify_otp, OTPVerificationError

router = APIRouter()


class RequestOTPPayload(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)


class VerifyOTPPayload(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    code: str = Field(..., min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    access_token: str
    role: str
    display_name: str
    market_name: str | None = None


@router.post("/request-otp", status_code=200)
def request_otp_endpoint(
    payload: RequestOTPPayload,
    db: Session = Depends(get_db),
):
    """
    POST /auth/request-otp

    Sends a 6-digit login code via SMS if this phone number is
    registered as an Identity (trader, head_of_traders, or wholesaler).

    Always returns the same generic response regardless of whether the
    phone is registered — this deliberately prevents using this
    endpoint to enumerate which phone numbers exist on the platform.
    See services/auth.py's request_otp docstring for the full reasoning.
    """
    request_otp(db, payload.phone)
    return {
        "message": (
            "If this phone number is registered, a login code has "
            "been sent via SMS."
        )
    }


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp_endpoint(
    payload: VerifyOTPPayload,
    db: Session = Depends(get_db),
):
    """
    POST /auth/verify-otp

    Verifies the code and, if valid, returns a session token plus the
    identity's role and display name so the frontend knows which
    dashboard to route to (trader / head-of-traders / wholesaler view).
    """
    try:
        result = verify_otp(db, payload.phone, payload.code)
    except OTPVerificationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return VerifyOTPResponse(**result)


# ============================================================
# ADMIN — CREATE HEAD OF TRADERS / WHOLESALER IDENTITIES
# ============================================================

class CreateIdentityPayload(BaseModel):
    """
    Admin-only. Creates a head_of_traders or wholesaler login.

    role must be exactly "head_of_traders" or "wholesaler" — this
    endpoint deliberately does NOT accept role="trader", since trader
    identities are always created automatically alongside a Trader
    row at POST /traders, never independently (see module docstring).
    """
    phone: str = Field(..., min_length=10, max_length=15)
    display_name: str = Field(..., min_length=2, max_length=200)
    role: str
    market_name: str | None = Field(
        default=None,
        description="Required if role=head_of_traders"
    )
    business_name: str | None = Field(
        default=None,
        description="Required if role=wholesaler"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("head_of_traders", "wholesaler"):
            raise ValueError(
                "role must be 'head_of_traders' or 'wholesaler'. "
                "Trader identities are created automatically at "
                "POST /traders, not through this endpoint."
            )
        return v


class CreateIdentityResponse(BaseModel):
    id: str
    phone: str
    display_name: str
    role: str
    market_name: str | None = None
    business_name: str | None = None


def verify_admin_key(x_admin_key: str = Header(default="")) -> None:
    """
    FastAPI dependency — gates admin-only endpoints behind a single
    shared key sent as the X-Admin-Key header. Deliberately simple:
    this is NOT a full admin role inside the Identity/JWT system —
    see core/config.py's ADMIN_API_KEY comment for why that scope was
    cut for the hackathon timeline.
    """
    if not x_admin_key or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid X-Admin-Key header."
        )


@router.post(
    "/identities",
    response_model=CreateIdentityResponse,
    status_code=201,
)
def create_identity(
    payload: CreateIdentityPayload,
    db: Session = Depends(get_db),
    _admin: None = Depends(verify_admin_key),
):
    """
    POST /auth/identities

    Admin-only (requires X-Admin-Key header). Creates a login identity
    for a Head of Traders or a Wholesaler.

    A Head of Traders MUST have market_name set — this is the market
    they will be scoped to when creating pools (enforced in
    routers/pools.py's create_pool, not here).

    A Wholesaler MUST have business_name set — this must exactly match
    the supplier_name used when a pool names them as supplier, since
    that string match is how confirm-order verifies ownership (see
    routers/pools.py's confirm_order docstring).
    """
    existing = db.query(Identity).filter(
        Identity.phone == payload.phone
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"An identity with phone {payload.phone} already "
                f"exists (role: {existing.role.value})."
            )
        )

    if payload.role == "head_of_traders" and not payload.market_name:
        raise HTTPException(
            status_code=422,
            detail="market_name is required when role=head_of_traders"
        )

    if payload.role == "wholesaler" and not payload.business_name:
        raise HTTPException(
            status_code=422,
            detail="business_name is required when role=wholesaler"
        )

    identity = Identity(
        phone=payload.phone,
        display_name=payload.display_name,
        role=IdentityRole(payload.role),
        market_name=payload.market_name,
        business_name=payload.business_name,
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)

    return CreateIdentityResponse(
        id=str(identity.id),
        phone=identity.phone,
        display_name=identity.display_name,
        role=identity.role.value,
        market_name=identity.market_name,
        business_name=identity.business_name,
    )
