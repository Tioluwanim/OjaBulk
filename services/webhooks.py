import os
import json
import hmac
import hashlib

from typing import Tuple

from fastapi import Request, HTTPException


class WebhookVerificationError(Exception):
    pass


class NombaWebhookService:

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

    def _generate_signature(
        self,
        payload: dict,
        timestamp: str,
    ) -> str:

        data = payload.get("data", {})
        merchant = data.get("merchant", {})
        transaction = data.get("transaction", {})

        event_type = payload.get(
            "event_type",
            ""
        )

        request_id = payload.get(
            "requestId",
            ""
        )

        user_id = merchant.get(
            "userId",
            ""
        )

        wallet_id = merchant.get(
            "walletId",
            ""
        )

        transaction_id = transaction.get(
            "transactionId",
            ""
        )

        transaction_type = transaction.get(
            "type",
            ""
        )

        transaction_time = transaction.get(
            "time",
            ""
        )

        response_code = transaction.get(
            "responseCode",
            ""
        )

        if response_code == "null":
            response_code = ""

        hashing_payload = (
            f"{event_type}:"
            f"{request_id}:"
            f"{user_id}:"
            f"{wallet_id}:"
            f"{transaction_id}:"
            f"{transaction_type}:"
            f"{transaction_time}:"
            f"{response_code}:"
            f"{timestamp}"
        )

        digest = hmac.new(
            self._get_secret().encode(),
            hashing_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return digest

    def verify(
        self,
        payload: dict,
        signature: str,
        timestamp: str,
    ) -> None:

        if not signature:
            raise WebhookVerificationError(
                "Missing nomba-signature header."
            )

        if not timestamp:
            raise WebhookVerificationError(
                "Missing nomba-timestamp header."
            )

        expected_signature = (
            self._generate_signature(
                payload,
                timestamp,
            )
        )

        if not hmac.compare_digest(
            expected_signature,
            signature,
        ):
            raise WebhookVerificationError(
                "Invalid webhook signature."
            )

    def parse_payload(
        self,
        body: dict
    ) -> dict:

        request_id = body.get(
            "requestId"
        )

        event_type = body.get(
            "event_type"
        )

        data = body.get(
            "data",
            {}
        )

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

        return (
            payload.get(
                "event_type"
            )
            == "payment_success"
        )


webhook_service = (
    NombaWebhookService()
)


async def get_raw_body_and_verify(
    request: Request
) -> Tuple[bytes, dict]:

    raw_body = await request.body()

    try:
        body = json.loads(
            raw_body.decode(
                "utf-8"
            )
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    signature = (
        request.headers.get(
            "nomba-signature",
            ""
        )
    )

    timestamp = (
        request.headers.get(
            "nomba-timestamp",
            ""
        )
    )

    try:
        webhook_service.verify(
            payload=body,
            signature=signature,
            timestamp=timestamp,
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )

    return raw_body, body
