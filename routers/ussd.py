"""
routers/ussd.py

Africa's Talking USSD session endpoint.
Africa's Talking sends form-encoded POST data, not JSON.
"""

from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse

from core.database import SessionLocal
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
        text:        cumulative input so far (empty on first dial,
                     then "1", "1*2", "1*2*Name", etc. as the caller
                     navigates deeper into a flow)

    Must return plain text starting with CON (session continues) or
    END (session terminates).

    Real change from the old read-only version: this now hands the DB
    session directly to services/ussd.py instead of only a
    phone-lookup closure, since the interactive flows (register, join
    a pool, join/create Esusu) need to run real queries and writes,
    not just look up a trader by phone.
    """
    db = SessionLocal()
    try:
        response = ussd_service.handle_session(
            db=db,
            session_id=sessionId,
            phone_number=phoneNumber,
            text=text,
        )
        return response
    finally:
        db.close()
