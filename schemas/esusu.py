from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator


class EsusuCycleCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    market_name: str = Field(..., min_length=2, max_length=200)
    contribution_amount: float = Field(..., gt=0)
    total_members: int = Field(..., ge=2, le=100)
    frequency_days: int = Field(default=7, ge=1, le=365)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("title", "market_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class EsusuContributeRequest(BaseModel):
    """
    FIX: previously POST /cycles/{id}/contribute took no body at all —
    a trader could just hit the endpoint and the system believed them
    that they'd paid, with no Payment row, no LedgerEntry, and nothing
    tied to a real Nomba-verified transfer. Now the caller must supply
    the nomba_transaction_ref of a real inbound payment (the same
    transaction_ref/requestId that Nomba's payment_success webhook
    already verified via HMAC and turned into a `Payment` row through
    the existing reconciliation pipeline — see engine/reconciliation.py
    and models/payment.py). services/esusu.py looks that Payment row up
    and rejects the contribution if it doesn't exist, doesn't belong to
    this trader, is short of the required amount, or has already been
    used for another contribution.
    """
    nomba_transaction_ref: str = Field(..., min_length=1, max_length=200)


class EsusuMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trader_id: str
    trader_name: str
    trader_phone: str
    payout_position: int
    joined_at: datetime | None = None
    last_contributed_round: int | None = None
    last_received_round: int | None = None


class EsusuContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    round_id: str
    trader_id: str
    trader_name: str
    amount: float
    contributed_at: datetime | None = None


class EsusuRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    round_number: int
    beneficiary_member_id: str
    beneficiary_trader_name: str
    target_amount: float
    collected_amount: float
    status: str
    created_at: datetime | None = None
    paid_at: datetime | None = None
    contribution_count: int
    progress_pct: float


class EsusuCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    market_name: str | None = None
    contribution_amount: float
    total_members: int
    frequency_days: int
    current_round_number: int
    status: str
    total_collected: float
    created_at: datetime | None = None
    activated_at: datetime | None = None
    completed_at: datetime | None = None
    members: list[EsusuMemberResponse]
    rounds: list[EsusuRoundResponse]
    contributions: list[EsusuContributionResponse]
    progress_pct: float
    next_beneficiary_trader_name: str | None = None


class EsusuListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    market_name: str | None = None
    contribution_amount: float
    total_members: int
    current_round_number: int
    status: str
    progress_pct: float
    created_at: datetime | None = None


class EsusuJoinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cycle_id: str
    trader_id: str
    trader_name: str
    payout_position: int
    status: str
    message: str


class EsusuContributionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycle_id: str
    round_number: int
    amount: float
    round_paid: bool
    cycle_completed: bool
    next_round_number: int | None = None
    beneficiary_trader_name: str