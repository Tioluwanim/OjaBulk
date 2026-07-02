"""
services/virtual_accounts.py

Manages Nomba virtual account provisioning for OjaBulk traders.

Design decisions:
- accountRef = trader's internal UUID (stable, our key, not Nomba's)
- Virtual accounts are static (permanent, reusable, no expectedAmount)
- This file only talks to Nomba — no DB writes, no SMS here
- Duplicate accountRef is handled gracefully (fetch existing instead of crash)
"""

import requests
import os
from services.client import nomba_client


class NombaVirtualAccountService:

    BASE_URL = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com/v1")
    VIRTUAL_ACCOUNTS_URL = f"{BASE_URL}/accounts/virtual"

    def create(
        self,
        trader_id: str,
        trader_name: str,
        callback_url: str | None = None,
    ) -> dict:
        """
        Creates a static virtual account for a trader.

        Args:
            trader_id:    Trader's internal UUID — used as accountRef
            trader_name:  Full name shown on the account
            callback_url: Optional webhook override per account (use global webhook if None)

        Returns:
            {
                "account_ref":         str,  # your trader_id echoed back
                "bank_name":           str,
                "bank_account_number": str,
                "bank_account_name":   str,
                "currency":            str,
            }
        """
        payload = {
            "accountRef": str(trader_id),
            "accountName": trader_name,
        }
        if callback_url:
            payload["callbackUrl"] = callback_url

        try:
            response = requests.post(
                self.VIRTUAL_ACCOUNTS_URL,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Virtual account creation request failed: {e}")

        # Handle duplicate accountRef gracefully — fetch existing instead of crashing
        if response.status_code == 409:
            return self.fetch(trader_id)

        if response.status_code not in (200, 201):
            raise PermissionError(
                f"Virtual account creation failed "
                f"[{response.status_code}]: {response.text}"
            )

        return self._parse_response(response.json())

    def fetch(self, trader_id: str) -> dict:
        """
        Fetches an existing virtual account by accountRef (trader UUID).

        Args:
            trader_id: Trader's internal UUID (used as accountRef at creation)

        Returns:
            Same dict shape as create()

        Raises:
            ValueError if no account found for this trader_id
        """
        url = f"{self.VIRTUAL_ACCOUNTS_URL}/{trader_id}"

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Virtual account fetch request failed: {e}")

        if response.status_code == 404:
            raise ValueError(
                f"No virtual account found for trader_id={trader_id}. "
                f"Has this trader been provisioned yet?"
            )

        if response.status_code != 200:
            raise PermissionError(
                f"Virtual account fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        return self._parse_response(response.json())

    def _parse_response(self, body: dict) -> dict:
        """
        Extracts only the fields OjaBulk needs from Nomba's response.
        Keeps the rest of the codebase insulated from Nomba's response shape.
        """
        try:
            data = body["data"]
            return {
                "account_ref":         data["accountRef"],
                "bank_name":           data.get("bankName", ""),
                "bank_account_number": data["bankAccountNumber"],
                "bank_account_name":   data.get("bankAccountName", ""),
                "currency":            data.get("currency", "NGN"),
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected virtual account response structure: {e}"
                f"\nFull response: {body}"
            )


# Single shared instance
virtual_account_service = NombaVirtualAccountService()


if __name__ == "__main__":
    import uuid
    print("Testing NombaVirtualAccountService...")

    test_trader_id = str(uuid.uuid4())
    print(f"Test trader ID (accountRef): {test_trader_id}")

    print("\n--- Creating virtual account ---")
    try:
        result = virtual_account_service.create(
            trader_id=test_trader_id,
            trader_name="Emeka Okafor Test",
        )
        print(f"Account number: {result['bank_account_number']}")
        print(f"Bank name:      {result['bank_name']}")
        print(f"Account name:   {result['bank_account_name']}")
        print(f"Account ref:    {result['account_ref']}")

        print("\n--- Fetching same account by accountRef ---")
        fetched = virtual_account_service.fetch(test_trader_id)
        print(f"Fetched number: {fetched['bank_account_number']}")
        match = fetched["bank_account_number"] == result["bank_account_number"]
        print(f"Create/fetch match: {match}")

        print("\n--- Testing duplicate create (should not crash) ---")
        duplicate = virtual_account_service.create(
            trader_id=test_trader_id,
            trader_name="Emeka Okafor Test",
        )
        print(f"Duplicate handled cleanly: {duplicate['bank_account_number']}")

    except Exception as e:
        print(f"Test failed: {e}")