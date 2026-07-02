"""
services/transfers.py

Nomba Transfers API — used exclusively for supplier payout when a pool hits target.

This file has one job: send money from OjaBulk's Nomba account
to a supplier's bank account. Nothing else.
"""

import requests
import os
from services.client import nomba_client


class NombaTransferService:

    BASE_URL = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com/v1")
    TRANSFERS_URL = f"{BASE_URL}/transfers/single"

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
        Sends pooled funds to a supplier's bank account.
        Called only by engine/payout.py when a pool reaches its target.

        Args:
            pool_id:                  Pool UUID — used as transfer reference
            pool_title:               Pool name — used in narration
            amount:                   Total naira to send (pool.current_locked_amount)
            supplier_account_number:  Supplier's NUBAN
            supplier_bank_code:       Supplier's bank code
            supplier_name:            Supplier's name for narration

        Returns:
            {
                "transfer_ref":   str,   # Nomba's reference for this transfer
                "status":         str,   # success / pending / failed
                "amount":         float,
            }

        Raises:
            ConnectionError: Network failure
            PermissionError: Auth or insufficient funds (4xx)
            ValueError:      Unexpected response structure
        """
        payload = {
            "amount":        str(int(amount * 100)),  # Nomba expects kobo (smallest unit)
            "bankCode":      supplier_bank_code,
            "accountNumber": supplier_account_number,
            "accountName":   supplier_name,
            "narration":     f"OjaBulk Pool Payout — {pool_title}",
            "merchantTxRef": f"pool-payout-{pool_id}",
            "currency":      "NGN",
        }

        try:
            response = requests.post(
                self.TRANSFERS_URL,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=30,  # Higher timeout — transfers can be slow
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Transfer request failed: {e}")

        if response.status_code not in (200, 201):
            raise PermissionError(
                f"Transfer failed [{response.status_code}]: {response.text}"
            )

        body = response.json()

        try:
            data = body.get("data", {})
            return {
                "transfer_ref": data.get("transactionReference", f"pool-payout-{pool_id}"),
                "status":       data.get("status", "success"),
                "amount":       amount,
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected transfer response structure: {e}"
                f"\nFull response: {body}"
            )

    def verify_bank_account(
        self,
        account_number: str,
        bank_code: str,
    ) -> dict:
        """
        Verifies a supplier's bank account before adding them to a pool.
        Prevents payouts to wrong accounts.

        Returns:
            {
                "account_number": str,
                "account_name":   str,
                "bank_code":      str,
            }
        """
        url = f"{self.BASE_URL}/transfers/banks/verify-account"

        try:
            response = requests.post(
                url,
                headers=nomba_client.get_headers(),
                json={
                    "accountNumber": account_number,
                    "bankCode":      bank_code,
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Bank verification request failed: {e}")

        if response.status_code != 200:
            raise PermissionError(
                f"Bank verification failed [{response.status_code}]: {response.text}"
            )

        body = response.json()
        try:
            data = body.get("data", {})
            return {
                "account_number": account_number,
                "account_name":   data.get("accountName", ""),
                "bank_code":      bank_code,
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected verification response: {e}\nFull: {body}"
            )


# Single shared instance
transfer_service = NombaTransferService()