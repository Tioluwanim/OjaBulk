import os
import requests

from services.client import nomba_client


class NombaTransferService:
    """
    Nomba Transfers API.

    Used for supplier payouts when a pool reaches target.
    """

    BASE_URL_V2 = os.getenv(
        "NOMBA_BASE_URL_V2",
        "https://sandbox.nomba.com/v2"
    ).rstrip("/")

    BASE_URL_V1 = os.getenv(
        "NOMBA_BASE_URL",
        "https://sandbox.nomba.com/v1"
    ).rstrip("/")

    TRANSFERS_URL = (
        f"{BASE_URL_V2}/transfers/bank"
    )

    def send_to_supplier(
        self,
        pool_id: str,
        pool_title: str,
        amount: float,
        supplier_account_number: str,
        supplier_bank_code: str,
        supplier_name: str,
    ) -> dict:
        """
        Send payout to supplier.
        """

        if amount <= 0:
            raise ValueError(
                "Transfer amount must be greater than zero."
            )

        merchant_tx_ref = (
            f"ojabulk-pool-payout-{pool_id}"
        )

        payload = {
            "amount": float(amount),
            "accountNumber": supplier_account_number,
            "accountName": supplier_name,
            "bankCode": supplier_bank_code,
            "merchantTxRef": merchant_tx_ref,
            "senderName": "OjaBulk",
            "narration": (
                f"OjaBulk Pool Payout - {pool_title}"
            )[:100],
        }

        try:
            response = requests.post(
                self.TRANSFERS_URL,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Transfer request failed: {e}"
            )

        print(
            f"[DEBUG] transfer status: "
            f"{response.status_code}"
        )
        print(
            f"[DEBUG] transfer body: "
            f"{response.text}"
        )

        try:
            body = response.json()
        except Exception:
            body = {}

        if response.status_code == 201:
            return {
                "transfer_ref": merchant_tx_ref,
                "status": "PROCESSING",
                "amount": amount,
                "is_pending": True,
            }

        if response.status_code != 200:
            raise PermissionError(
                f"Transfer failed "
                f"[{response.status_code}]: "
                f"{response.text}"
            )

        data = body.get("data", {})

        return {
            "transfer_ref": data.get(
                "id",
                merchant_tx_ref
            ),
            "status": data.get(
                "status",
                "SUCCESS"
            ),
            "amount": amount,
            "is_pending": False,
        }

    def requery_transfer(
        self,
        transaction_ref: str,
        sub_account_id: str | None = None,
    ) -> dict:
        """
        Requery transfer status.

        Verify this endpoint against your
        Nomba dashboard documentation.
        """

        if sub_account_id:
            url = (
                f"{self.BASE_URL_V1}"
                f"/transactions/accounts/"
                f"{sub_account_id}/single"
            )
        else:
            url = (
                f"{self.BASE_URL_V1}"
                f"/transactions/accounts/single"
            )

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                params={
                    "transactionRef": transaction_ref
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Transfer requery failed: {e}"
            )

        print(
            f"[DEBUG] requery status: "
            f"{response.status_code}"
        )
        print(
            f"[DEBUG] requery body: "
            f"{response.text}"
        )

        if response.status_code != 200:
            raise PermissionError(
                f"Transfer requery failed "
                f"[{response.status_code}]: "
                f"{response.text}"
            )

        body = response.json()
        data = body.get("data", {})

        return {
            "transfer_ref": transaction_ref,
            "status": data.get(
                "status",
                "UNKNOWN"
            ),
            "raw": data,
        }

    def get_banks(self) -> list:
        """
        Fetch supported banks.

        Confirm endpoint path from docs.
        """

        url = (
            f"{self.BASE_URL_V1}"
            f"/transfers/banks"
        )

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Bank list request failed: {e}"
            )

        print(
            f"[DEBUG] banks status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            raise PermissionError(
                f"Bank list failed "
                f"[{response.status_code}]: "
                f"{response.text}"
            )

        body = response.json()

        return body.get(
            "data",
            []
        )


transfer_service = (
    NombaTransferService()
)


if __name__ == "__main__":

    print(
        "Testing NombaTransferService..."
    )

    try:

        banks = (
            transfer_service.get_banks()
        )

        print(
            f"Banks returned: "
            f"{len(banks)}"
        )

        if banks:
            print(
                "First bank:"
            )
            print(
                banks[0]
            )

    except Exception as e:
        print(
            f"Test failed: {e}"
        )