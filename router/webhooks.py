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
from services.webhook import webhook_service, WebhookVerificationError
from engine.reconciliation import (
    reconcile,
    PaymentAlreadyProcessedError,
    TraderNotFoundError,
)

router = APIRouter()


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
    # Step 1 — Read raw body (must be raw for HMAC verification)
    raw_body = await request.body()

    # Step 2 — Verify HMAC signature
    signature = request.headers.get("x-nomba-signature", "")
    try:
        webhook_service.verify(raw_body, signature)
    except WebhookVerificationError as e:
        # Log but do not expose details to caller
        print(f"[Webhook] Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Step 3 — Parse body
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Step 4 — Parse payload fields
    try:
        payload = webhook_service.parse_payload(body)
    except ValueError as e:
        print(f"[Webhook] Payload parse error: {e}")
        # Return 200 anyway — malformed payload should not cause Nomba retries
        return {"status": "received", "note": "payload parse error — logged"}

    # Step 5 — Return 200 IMMEDIATELY
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