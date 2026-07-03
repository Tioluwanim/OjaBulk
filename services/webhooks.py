import hmac
import hashlib
import json
import os

from typing import Optional, Tuple

from fastapi import Request, HTTPException


class WebhookVerificationError(Exception):
    """Raised when webhook verification fails."""
    pass


class NombaWebhookService:
    """
    Nomba webhook verification and payload parsing.
    """

    def __init__(self):
        self.signing_secret = os.getenv(
            "NOMBA_WEBHOOK_SECRET",
            ""
        )

    def _get_secret(self) -> str:
        if not self.signing_secret:
            raise WebhookVerificationError(
                "NOMBA_WEBHOOK_SECRET is not configured."
            )

        return self.signing_secret

    def _compute_signature(
        self,
        raw_body: bytes
    ) -> str:
        """
        Compute HMAC SHA256 signature.
        """

        secret = self._get_secret()

        return hmac.new(
            key=secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def verify(
        self,
        raw_body: bytes,
        nomba_signature: str,
    ) -> None:
        """
        Verify Nomba webhook signature.
        """

        if not nomba_signature:
            raise WebhookVerificationError(
                "Missing x-nomba-signature header."
            )

        expected = self._compute_signature(
            raw_body
        )

        if not hmac.compare_digest(
            expected,
            nomba_signature,
        ):
            raise WebhookVerificationError(
                "Invalid webhook signature."
            )

    def parse_payload(
        self,
        body: dict
    ) -> dict:
        """
        Extract OjaBulk fields from webhook.
        """

        request_id = body.get("requestId")
        event_type = body.get("event_type")

        data = body.get("data", {})
        transaction = data.get(
            "transaction",
            {}
        )
        customer = data.get(
            "customer",
            {}
        )

        virtual_account_number = (
            transaction.get(
                "aliasAccountNumber"
            )
        )

        amount = transaction.get(
            "transactionAmount"
        )

        if not request_id:
            raise ValueError(
                "Missing requestId"
            )

        if not virtual_account_number:
            raise ValueError(
                "Missing aliasAccountNumber"
            )

        if amount is None:
            raise ValueError(
                "Missing transactionAmount"
            )

        return {
            "event_type": str(
                event_type or ""
            ),
            "transaction_ref": str(
                request_id
            ),
            "virtual_account_number": str(
                virtual_account_number
            ),
            "amount": float(amount),
            "sender_name": customer.get(
                "senderName"
            ),
            "sender_bank": customer.get(
                "bankName"
            ),
            "sender_account_number": customer.get(
                "accountNumber"
            ),
            "narration": transaction.get(
                "narration"
            ),
            "session_id": transaction.get(
                "sessionId"
            ),
            "transaction_id": transaction.get(
                "transactionId"
            ),
        }

    def is_payment_success(
        self,
        payload: dict
    ) -> bool:
        """
        Check if webhook represents
        a successful payment.
        """

        return (
            payload.get("event_type")
            == "payment_success"
        )


webhook_service = (
    NombaWebhookService()
)


async def get_raw_body_and_verify(
    request: Request
) -> Tuple[bytes, dict]:
    """
    FastAPI helper for webhook routes.
    """

    raw_body = await request.body()

    signature = request.headers.get(
        "x-nomba-signature",
        ""
    )

    try:
        webhook_service.verify(
            raw_body,
            signature,
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )

    try:
        body = json.loads(
            raw_body.decode("utf-8")
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    return raw_body, body