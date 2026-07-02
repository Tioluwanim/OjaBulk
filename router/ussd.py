"""
routers/ussd.py

Africa's Talking USSD session endpoint.
Africa's Talking sends form-encoded POST data, not JSON.
"""

from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.trader import Trader
from services.ussd import ussd_service

router = APIRouter()


@router.post("/session", response_class=PlainTextResponse)
async def ussd_session(
    sessionId:   str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text:        str = Form(default=""),
):
    """
    POST /ussd/session

    Africa's Talking sends:
        sessionId:   unique session identifier
        serviceCode: your USSD code e.g. *384#
        phoneNumber: caller's number e.g. +2348012345678
        text:        cumulative input so far (empty on first dial)

    Must return plain text starting with CON or END.
    """
    db = SessionLocal()
    try:
        def get_trader_by_phone(phone: str):
            # Normalize: strip +234 prefix, handle 0XX format
            normalized = phone.replace("+234", "0").replace(" ", "")
            return db.query(Trader).filter(
                Trader.phone.in_([phone, normalized])
            ).first()

        response = ussd_service.handle_session(
            session_id=sessionId,
            phone_number=phoneNumber,
            text=text,
            get_trader_by_phone=get_trader_by_phone,
        )
        return response
    finally:
        db.close()