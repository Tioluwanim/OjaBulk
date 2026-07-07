import os
import requests

from services.client import nomba_client


class NombaTransferService:
    """
    Nomba Transfers API.

    Used for supplier payouts when a pool reaches target.

    CORRECTED per the Nomba hackathon organizer's confirmed API reference:
    the transfer endpoint must be scoped to the sub-account that actually
    holds the pooled funds — POST /v2/transfers/bank/{subAccountId} — not
    the parent-account endpoint (POST /v2/transfers/bank with no path
    param). Since every trader virtual account is created under
    /accounts/virtual/{subAccountId}, the money genuinely lands in the
    sub-account, not the parent. A payout call against the parent
    endpoint would either fail (insufficient parent balance) or, worse,
    silently draw from the wrong pool of money if the parent happens to
    have unrelated funds.
    """

    BASE_URL_V2 = os.getenv(
        "NOMBA_BASE_URL_V2",
        "https://sandbox.nomba.com/v2"
    ).rstrip("/")

    BASE_URL_V1 = os.getenv(
        "NOMBA_BASE_URL",
        "https://sandbox.nomba.com/v1"
    ).rstrip("/")

    def _transfer_url(self) -> str:
        """
        Sub-account-scoped transfer URL, per organizer spec:
        POST /v2/transfers/bank/{subAccountId}
        """
        return f"{self.BASE_URL_V2}/transfers/bank/{nomba_client.subaccount_id}"

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
        Send payout to supplier from the sub-account holding pooled funds.
        """
        return self._send_bank_transfer(
            merchant_tx_ref=f"ojabulk-pool-payout-{pool_id}",
            amount=amount,
            account_number=supplier_account_number,
            account_name=supplier_name,
            bank_code=supplier_bank_code,
            narration=f"OjaBulk Pool Payout - {pool_title}"[:100],
        )

    def send_to_trader(
        self,
        round_id: str,
        cycle_title: str,
        amount: float,
        trader_account_number: str,
        trader_bank_code: str,
        trader_account_name: str,
    ) -> dict:
        """
        Send an Esusu/Ajo round payout directly to a beneficiary
        trader's own registered bank account — the same Nomba Transfer
        API and sub-account used for send_to_supplier() above, just a
        different recipient and merchant_tx_ref namespace so the two
        payout types never collide or get confused in Nomba's
        dashboard/requery.
        """
        return self._send_bank_transfer(
            merchant_tx_ref=f"ojabulk-esusu-payout-{round_id}",
            amount=amount,
            account_number=trader_account_number,
            account_name=trader_account_name,
            bank_code=trader_bank_code,
            narration=f"OjaBulk Esusu Payout - {cycle_title}"[:100],
        )

    def _send_bank_transfer(
        self,
        merchant_tx_ref: str,
        amount: float,
        account_number: str,
        account_name: str,
        bank_code: str,
        narration: str,
    ) -> dict:
        """
        Shared bank-transfer call used by both send_to_supplier() and
        send_to_trader() — identical Nomba request shape, only the
        recipient and merchant_tx_ref differ.
        """

        if amount <= 0:
            raise ValueError(
                "Transfer amount must be greater than zero."
            )

        payload = {
            "amount": float(amount),
            "accountNumber": account_number,
            "accountName": account_name,
            "bankCode": bank_code,
            "merchantTxRef": merchant_tx_ref,
            "senderName": "OjaBulk",
            "narration": narration,
        }

        url = self._transfer_url()

        try:
            response = requests.post(
                url,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Transfer request failed: {e}"
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
    ) -> dict:
        """
        Requery transfer status, scoped to our sub-account.

        Per organizer spec: GET /v1/transactions/accounts/{subAccountId}
        "If you use both parent and sub account to carry out transfers,
        use this" (per Nomba docs) — since OjaBulk transfers exclusively
        from the sub-account, this is always scoped to subaccount_id.
        """
        url = (
            f"{self.BASE_URL_V1}"
            f"/transactions/accounts/"
            f"{nomba_client.subaccount_id}/single"
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
        Fetch supported banks. Per organizer spec:
        GET /v1/transfers/banks (not sub-account-scoped — this is a
        static reference list, not account-specific data).
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

    def lookup_account(
        self,
        account_number: str,
        bank_code: str,
    ) -> dict:
        """
        Verify a recipient bank account before transferring — confirmed
        endpoint per organizer spec: POST /v1/transfers/bank/lookup.
        Always call this before adding a supplier to a pool, so the
        admin can confirm the account name matches before real money
        moves.
        """
        url = f"{self.BASE_URL_V1}/transfers/bank/lookup"

        try:
            response = requests.post(
                url,
                headers=nomba_client.get_headers(),
                json={
                    "accountNumber": account_number,
                    "bankCode": bank_code,
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Bank lookup failed: {e}")

        if response.status_code != 200:
            raise PermissionError(
                f"Bank lookup failed [{response.status_code}]: {response.text}"
            )

        body = response.json()
        data = body.get("data", {})
        return {
            "account_number": data.get("accountNumber", account_number),
            "account_name": data.get("accountName", ""),
        }


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