"""
services/webhooks.py

Nomba webhook HMAC signature verification.

Security contract:
- Every inbound webhook MUST pass HMAC verification before any business logic runs
- Verification uses constant-time comparison to prevent timing attacks
- Failed verification raises WebhookVerificationError immediately
- This file has zero knowledge of traders, pools, or ledgers
"""

import hmac
import hashlib
import os
from fastapi import Request, HTTPException


class WebhookVerificationError(Exception):
    """Raised when a webhook fails HMAC verification."""
    pass


class NombaWebhookService:

    def __init__(self):
        self.signing_secret = os.getenv("NOMBA_WEBHOOK_SECRET", "")
        if not self.signing_secret:
            raise EnvironmentError(
                "NOMBA_WEBHOOK_SECRET not set in .env. "
                "Get this from your Nomba dashboard webhook settings."
            )

    def _compute_signature(self, raw_body: bytes) -> str:
        """
        Computes HMAC-SHA256 of the raw request body using the signing secret.
        Both Nomba and our backend compute this independently.
        If they match, the webhook is authentic.
        """
        return hmac.new(
            key=self.signing_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def verify(self, raw_body: bytes, nomba_signature: str) -> None:
        """
        Verifies the webhook signature from Nomba.

        Args:
            raw_body:        The raw bytes of the request body — MUST be raw,
                             not parsed JSON. Parsing before hashing breaks verification.
            nomba_signature: The signature header value Nomba sent

        Raises:
            WebhookVerificationError: If signature does not match
        """
        if not nomba_signature:
            raise WebhookVerificationError(
                "No signature header present on webhook request. "
                "Rejecting — unauthenticated requests are never processed."
            )

        expected = self._compute_signature(raw_body)

        # Constant-time comparison — prevents timing attacks
        # Never use == for signature comparison
        if not hmac.compare_digest(expected, nomba_signature):
            raise WebhookVerificationError(
                "Webhook signature mismatch. "
                "Request did not originate from Nomba or body was tampered with."
            )

    def parse_payload(self, body: dict) -> dict:
        """
        Extracts the fields OjaBulk needs from a verified Nomba webhook payload.

        Returns:
            {
                "virtual_account_number": str,
                "amount":                 float,
                "transaction_ref":        str,   # idempotency key
                "event_type":             str,
            }

        Raises:
            ValueError if required fields are missing from the payload
        """
        try:
            # Nomba webhook payload shape — adjust field names to match
            # actual Nomba webhook docs once confirmed from sandbox testing
            data = body.get("data", body)

            virtual_account_number = (
                data.get("virtualAccountNumber")
                or data.get("accountNumber")
                or data.get("destinationAccountNumber")
            )
            amount = data.get("amount") or data.get("transactionAmount")
            transaction_ref = (
                data.get("transactionReference")
                or data.get("transactionRef")
                or data.get("requestId")
            )
            event_type = body.get("event_type") or body.get("eventType", "payment_success")

            if not virtual_account_number:
                raise ValueError("No virtual account number in webhook payload")
            if amount is None:
                raise ValueError("No amount in webhook payload")
            if not transaction_ref:
                raise ValueError("No transaction reference in webhook payload")

            return {
                "virtual_account_number": str(virtual_account_number),
                "amount":                 float(amount),
                "transaction_ref":        str(transaction_ref),
                "event_type":             str(event_type),
            }

        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Failed to parse webhook payload: {e}"
                f"\nFull payload: {body}"
            )


async def get_raw_body_and_verify(request: Request) -> tuple[bytes, dict]:
    """
    FastAPI dependency — reads raw body, verifies signature, returns parsed dict.

    Usage in router:
        @router.post("/webhooks/nomba")
        async def handle_webhook(raw_body: bytes = Depends(get_raw_body), ...):

    Returns:
        (raw_body_bytes, parsed_payload_dict)

    Raises:
        HTTPException 401 if verification fails
    """
    raw_body = await request.body()
    signature = request.headers.get("x-nomba-signature", "")

    try:
        webhook_service.verify(raw_body, signature)
    except WebhookVerificationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    import json
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in webhook body")

    return raw_body, body


# Single shared instance
webhook_service = NombaWebhookService()