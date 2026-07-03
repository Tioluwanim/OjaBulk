import os
import requests

from services.client import nomba_client


class NombaSubAccountService:
    """
    Operations that require an existing Nomba sub-account.

    Supported endpoints:
    - GET /v1/accounts/{subAccountId}/balance
    - GET /v1/transactions/accounts/{subAccountId}
    """

    BASE_URL = os.getenv(
        "NOMBA_BASE_URL",
        "https://sandbox.nomba.com/v1"
    ).rstrip("/")

    def get_subaccount_balance(self, subaccount_id: str) -> dict:
        """
        Fetch balance for a sub-account.
        """

        url = f"{self.BASE_URL}/accounts/{subaccount_id}/balance"

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Balance fetch failed: {e}"
            )

        print(f"[DEBUG] balance url: {url}")
        print(f"[DEBUG] balance status: {response.status_code}")
        print(f"[DEBUG] balance body: {response.text}")

        if response.status_code != 200:
            raise PermissionError(
                f"Balance fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()
        data = body.get("data", {})

        return {
            "subaccount_id": subaccount_id,
            "amount": float(data.get("amount", 0)),
            "currency": data.get("currency", "NGN"),
            "time_created": data.get("timeCreated")
        }

    def get_transactions(self, subaccount_id: str) -> dict:
        """
        Fetch transactions for a sub-account.
        """

        url = (
            f"{self.BASE_URL}/transactions/accounts/{subaccount_id}"
        )

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Transaction fetch failed: {e}"
            )

        print(f"[DEBUG] txn url: {url}")
        print(f"[DEBUG] txn status: {response.status_code}")
        print(f"[DEBUG] txn body: {response.text}")

        if response.status_code != 200:
            raise PermissionError(
                f"Transaction fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        return response.json()

    def verify_against_ledger(
        self,
        subaccount_id: str,
        our_locked_amount: float
    ) -> dict:
        """
        Compare Nomba balance against OjaBulk ledger.
        """

        balance = self.get_subaccount_balance(
            subaccount_id
        )

        nomba_balance = balance["amount"]

        discrepancy = abs(
            nomba_balance - our_locked_amount
        )

        return {
            "subaccount_id": subaccount_id,
            "nomba_balance": nomba_balance,
            "our_ledger": our_locked_amount,
            "discrepancy": discrepancy,
            "is_reconciled": discrepancy < 0.01
        }


sub_account_service = NombaSubAccountService()


if __name__ == "__main__":

    SUBACCOUNT_ID = os.getenv(
        "NOMBA_SUB_ACCOUNT_ID"
    )

    if not SUBACCOUNT_ID:
        raise EnvironmentError(
            "NOMBA_SUB_ACCOUNT_ID is required"
        )

    print("Testing Nomba Sub-Account APIs...")
    print(f"Base URL: {sub_account_service.BASE_URL}")
    print(f"Sub Account: {SUBACCOUNT_ID}")

    try:
        print("\n--- Balance ---")

        balance = (
            sub_account_service.get_subaccount_balance(
                SUBACCOUNT_ID
            )
        )

        print(
            f"Balance: ₦{balance['amount']:,.2f}"
        )
        print(
            f"Currency: {balance['currency']}"
        )
        print(
            f"Created: {balance['time_created']}"
        )

        print("\n--- Reconciliation Check ---")

        check = (
            sub_account_service.verify_against_ledger(
                subaccount_id=SUBACCOUNT_ID,
                our_locked_amount=0.0
            )
        )

        print(
            f"Nomba Balance: ₦{check['nomba_balance']:,.2f}"
        )
        print(
            f"Our Ledger: ₦{check['our_ledger']:,.2f}"
        )
        print(
            f"Discrepancy: ₦{check['discrepancy']:,.2f}"
        )
        print(
            f"Reconciled: {check['is_reconciled']}"
        )

        print("\n--- Transactions ---")

        transactions = (
            sub_account_service.get_transactions(
                SUBACCOUNT_ID
            )
        )

        print(transactions)

    except Exception as e:
        print(f"Test failed: {e}")