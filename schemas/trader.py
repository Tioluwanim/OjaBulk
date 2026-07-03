"""
schemas/trader.py

Pydantic schemas for Trader endpoints.

Split principle: "Create" schemas define what a client is allowed to
send. "Response" schemas define what we send back. Fields like
spendable_balance never appear in a Create schema — they are set
only by backend logic, never by client input.

IMPORTANT: every Response schema must set `Config.from_attributes = True`.
Without it, Pydantic cannot read attributes off a SQLAlchemy ORM object
(e.g. entry.note, entry.entry_type) when that object is passed in directly
instead of a plain dict. Missing this on ANY response schema is the most
common source of validation errors in this file — this bug happened once
already on LedgerEntryResponse, so every schema below is checked.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TraderCreate(BaseModel):
    """What a client may submit to POST /traders"""
    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    stall_number: str = Field(..., min_length=1, max_length=50)
    market_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        """
        Normalizes every phone number to the canonical storage format:
        0XXXXXXXXXX (11 digits, leading 0 — standard Nigerian local format).
        """
        v = v.strip().replace(" ", "").replace("-", "")

        if v.startswith("+234"):
            v = "0" + v[4:]
        elif v.startswith("234") and len(v) == 13:
            v = "0" + v[3:]

        if not v.isdigit():
            raise ValueError("phone must contain only digits")
        if not v.startswith("0") or len(v) != 11:
            raise ValueError(
                "phone must be a valid Nigerian number "
                "(11 digits starting with 0, e.g. 08012345678)"
            )
        return v

    @field_validator("name", "stall_number", "market_name")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class TraderResponse(BaseModel):
    """What we return for a single trader"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    stall_number: str
    market_name: str
    virtual_account_number: str | None = None
    bank_name: str | None = None
    bank_account_name: str | None = None
    spendable_balance: float
    total_contributed: float
    created_at: datetime | None = None


class TraderListItem(BaseModel):
    """Lighter shape used in GET /traders list view"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    stall_number: str
    market_name: str
    virtual_account_number: str | None = None
    bank_name: str | None = None
    spendable_balance: float
    total_contributed: float


class LedgerEntryResponse(BaseModel):
    """
    Fixed: added from_attributes=True.
    Without this, constructing this schema from a SQLAlchemy LedgerEntry
    ORM object (rather than plain kwargs) fails validation on fields
    like `note`, because Pydantic v2 does not read arbitrary object
    attributes unless from_attributes is explicitly enabled.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    entry_type: str
    amount: float
    balance_after: float
    note: str | None = None
    pool_id: str | None = None
    created_at: datetime


class TraderLedgerResponse(BaseModel):
    """Fixed: added from_attributes=True for consistency and safety."""
    model_config = ConfigDict(from_attributes=True)

    trader_id: str
    trader_name: str
    current_spendable: float
    entries: list[LedgerEntryResponse]
