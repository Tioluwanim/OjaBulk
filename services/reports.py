"""
services/reports.py

Fetches real Nomba account balance for the reconciliation report.

The reconciliation report compares:
    sum(all trader spendable_balances) + sum(all open pool current_locked_amounts)
    vs
    real Nomba account balance from this service

If they match — our ledger is provably correct.
"""

import requests
import os
from services.client import nomba_client


class NombaReportsService:

    BASE_URL = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com/v1")
    BALANCE_URL = f"{BASE_URL}/accounts/balance"

    def get_account_balance(self) -> dict:
        """
        Fetches the real balance of OjaBulk's parent Nomba account.

        Returns:
            {
                "amount":       float,
                "currency":     str,
                "time_created": str,
            }

        Raises:
            ConnectionError: Network failure
            PermissionError: Auth failure
            ValueError:      Unexpected response structure
        """
        try:
            response = requests.get(
                self.BALANCE_URL,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Balance fetch request failed: {e}")

        if response.status_code != 200:
            raise PermissionError(
                f"Account balance fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()

        try:
            data = body["data"]
            return {
                "amount":       float(data["amount"]),
                "currency":     data.get("currency", "NGN"),
                "time_created": data.get("timeCreated", ""),
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected balance response structure: {e}"
                f"\nFull response: {body}"
            )

    def reconcile(self, our_ledger_total: float) -> dict:
        """
        Compares our PostgreSQL ledger total against the real Nomba balance.

        Args:
            our_ledger_total: sum(spendable_balance) + sum(current_locked_amount)
                              computed from our PostgreSQL tables

        Returns:
            {
                "nomba_balance":    float,
                "our_ledger_total": float,
                "discrepancy":      float,   # 0.0 = perfect match
                "is_reconciled":    bool,
                "currency":         str,
                "checked_at":       str,
            }
        """
        from datetime import datetime, timezone

        balance_data = self.get_account_balance()
        nomba_balance = balance_data["amount"]
        discrepancy = abs(nomba_balance - our_ledger_total)

        return {
            "nomba_balance":    nomba_balance,
            "our_ledger_total": our_ledger_total,
            "discrepancy":      discrepancy,
            "is_reconciled":    discrepancy == 0.0,
            "currency":         balance_data["currency"],
            "checked_at":       datetime.now(timezone.utc).isoformat(),
        }


# Single shared instance
reports_service = NombaReportsService()