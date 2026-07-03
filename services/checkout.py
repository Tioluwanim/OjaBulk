"""
services/checkout.py

Nomba Checkout Service

Endpoints:
    POST /v1/checkout/order
    GET  /v1/checkout/order/{orderReference}

Reference:
    https://developer.nomba.com

Purpose:
    Create hosted checkout links for card/transfer payments.
"""

import os
import uuid
import requests

from services.client import nomba_client


class NombaCheckoutService:

    BASE_URL = os.getenv(
        "NOMBA_BASE_URL",
        "https://sandbox.nomba.com/v1"
    ).rstrip("/")

    def create_order(
        self,
        amount: float,
        customer_email: str,
        callback_url: str,
        customer_id: str | None = None,
        allowed_payment_methods: list[str] | None = None,
        tokenize_card: bool = False,
        metadata: dict | None = None,
    ) -> dict:
        """
        Create a checkout order.

        Args:
            amount: Amount in NGN
            customer_email: Customer email
            callback_url: Redirect/webhook callback
            customer_id: Internal user ID
            allowed_payment_methods: ["Card", "Transfer"]
            tokenize_card: Save card for recurring payments
            metadata: Additional metadata

        Returns:
            {
                "checkout_link": str,
                "order_reference": str
            }
        """

        url = f"{self.BASE_URL}/checkout/order"

        order_reference = str(uuid.uuid4())

        payload = {
            "order": {
                "callbackUrl": callback_url,
                "customerEmail": customer_email,
                "amount": f"{amount:.2f}",
                "currency": "NGN",
                "orderReference": order_reference,
                "customerId": customer_id or order_reference,
                "accountId": nomba_client.account_id,
                "allowedPaymentMethods": (
                    allowed_payment_methods
                    or ["Card", "Transfer"]
                ),
                "orderMetaData": metadata or {},
            },
            "tokenizeCard": tokenize_card,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=nomba_client.get_headers(),
                timeout=20,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Checkout creation failed: {e}"
            )

        print(f"[DEBUG] create status: {response.status_code}")
        print(f"[DEBUG] create body: {response.text}")

        if response.status_code not in (200, 201):
            raise PermissionError(
                f"Checkout creation failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()

        try:
            data = body["data"]

            return {
                "checkout_link": data["checkoutLink"],
                "order_reference": data["orderReference"],
            }

        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected checkout response: {e}\n"
                f"Full response: {body}"
            )

    def get_order_status(
        self,
        order_reference: str,
    ) -> dict:
        """
        Fetch order status.
        """

        url = (
            f"{self.BASE_URL}"
            f"/checkout/order/{order_reference}"
        )

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=20,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Order lookup failed: {e}"
            )

        print(f"[DEBUG] status code: {response.status_code}")
        print(f"[DEBUG] status body: {response.text}")

        if response.status_code != 200:
            raise PermissionError(
                f"Order lookup failed "
                f"[{response.status_code}]: {response.text}"
            )

        return response.json()


checkout_service = NombaCheckoutService()


if __name__ == "__main__":

    print("Testing Nomba Checkout Service...")

    try:

        result = checkout_service.create_order(
            amount=1000.00,
            customer_email="test@example.com",
            callback_url="https://your-ngrok-url.ngrok-free.app/api/webhooks/nomba",
            customer_id="test-user-001",
            metadata={
                "source": "OjaBulk",
                "poolId": "pool-001",
            },
        )

        print("\n--- Checkout Created ---")
        print(
            f"Order Reference: {result['order_reference']}"
        )
        print(
            f"Checkout Link: {result['checkout_link']}"
        )

        print("\n--- Order Status ---")

        status = checkout_service.get_order_status(
            result["order_reference"]
        )

        print(status)

    except Exception as e:
        print(f"Test failed: {e}")