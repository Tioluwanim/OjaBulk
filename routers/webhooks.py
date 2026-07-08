"""
routers/webhooks.py

Nomba payment webhook endpoint.

Critical rules:
1. Return 200 IMMEDIATELY after verification — before reconciliation runs
2. All reconciliation happens in a BackgroundTask
3. Never let reconciliation errors surface as non-200 responses to Nomba
   (non-200 causes Nomba to retry, which causes duplicate webhook delivery)
"""

import json
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.payment import Payment
from services.webhooks import webhook_service, WebhookVerificationError
from engine.reconciliation import (
    reconcile,
    PaymentAlreadyProcessedError,
    TraderNotFoundError,
)

router = APIRouter()


def _get_header_value(headers, *names: str) -> str:
    for name in names:
        value = headers.get(name, "")
        if value:
            return value

    return ""


@router.post("/nomba")
async def receive_nomba_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    POST /webhooks/nomba

    Entry point for all Nomba payment notifications.
    Processes every inbound transfer to any trader's virtual account.
    """
    # Step 1 — Read raw body
    raw_body = await request.body()

    # Step 2 — Parse body (Required first because verify() needs a dict)
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Step 3 — Verify HMAC signature
    signature = _get_header_value(
        request.headers,
        "nomba-signature",
        "x-nomba-signature",
    )
    timestamp = _get_header_value(
        request.headers,
        "nomba-timestamp",
        "x-nomba-timestamp",
    )
    
    try:
        webhook_service.verify(
            payload=body,
            signature=signature,
            timestamp=timestamp
        )
    except WebhookVerificationError as e:
        # Log but do not expose details to caller
        print(f"[Webhook] Verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Step 4 — Parse payload fields
    try:
        payload = webhook_service.parse_payload(body)
    except ValueError as e:
        print(f"[Webhook] Payload parse error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Step 5 — Idempotency check before the background task is queued.
    db = SessionLocal()
    try:
        existing_payment = db.query(Payment).filter(
            Payment.nomba_transaction_ref == payload["transaction_ref"]
        ).first()
    finally:
        db.close()

    if existing_payment:
        return {
            "status": "received",
            "note": "duplicate transaction ignored",
        }

    # Step 5b — Only reconcile actual inbound-payment events.
    #
    # FIX: Nomba fires this same webhook URL for every subscribed
    # event type — payment_success, payout_success, payment_failed,
    # payment_reversal, payout_failed, payout_refund (see
    # https://developer.nomba.com/products/webhooks/introduction).
    # This handler only ever means one thing when it reconciles: money
    # arrived in a trader's virtual account. Previously ANY event type
    # reached reconcile() — including payout_success firing for our
    # OWN outbound supplier payouts — which would have credited a
    # trader's spendable/pool balance for a payment that was never
    # actually received. webhook_service.is_payment_success() already
    # existed for exactly this check but was never called anywhere.
    if not webhook_service.is_payment_success(payload):
        print(
            f"[Webhook] Ignoring non-payment_success event "
            f"'{payload.get('event_type')}' for "
            f"{payload['transaction_ref']} — not reconciled."
        )
        return {
            "status": "received",
            "note": f"event_type '{payload.get('event_type')}' not reconciled",
        }

    # Step 6 — Return 200 IMMEDIATELY
    # Nomba considers the webhook delivered when it receives 200.
    # Reconciliation runs in background — Nomba never waits for it.
    background_tasks.add_task(
        _run_reconciliation,
        virtual_account_number=payload["virtual_account_number"],
        amount_received=payload["amount"],
        transaction_ref=payload["transaction_ref"],
    )

    return {"status": "received"}


async def _run_reconciliation(
    virtual_account_number: str,
    amount_received: float,
    transaction_ref: str,
):
    """
    Background task — runs after 200 is returned to Nomba.
    Creates its own DB session since it runs outside the request lifecycle.
    """
    db = SessionLocal()
    try:
        result = reconcile(
            db=db,
            virtual_account_number=virtual_account_number,
            amount_received=amount_received,
            transaction_ref=transaction_ref,
        )
        print(
            f"[Webhook] Reconciled {transaction_ref}: "
            f"pool=₦{result['pool_cut']:,.0f} "
            f"spendable=₦{result['spendable_cut']:,.0f} "
            f"fulfilled={result['pool_fulfilled']}"
        )
    except PaymentAlreadyProcessedError as e:
        print(f"[Webhook] Duplicate ignored: {e}")
    except TraderNotFoundError as e:
        print(f"[Webhook] Unknown account — manual review needed: {e}")
    except Exception as e:
        print(f"[Webhook] Reconciliation error for {transaction_ref}: {e}")
    finally:
        db.close()
