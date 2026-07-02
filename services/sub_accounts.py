import requests
import os
from services.client import nomba_client


class NombaSubAccountService:
    """
    Manages Nomba sub-accounts for OjaBulk pools.

    Each pool gets its own sub-account so locked funds
    are tracked at the Nomba level — not just in our ledger.

    Sub-accounts use your parent accountId in the header
    and return their own ID for scoping further calls.
    """

    BASE_URL = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com/v1")
    SUBACCOUNTS_URL = f"{BASE_URL}/accounts/sub-accounts"

    def create_pool_subaccount(
        self,
        pool_id: str,
        pool_title: str,
    ) -> dict:
        """
        Creates a sub-account for a new pool.
        Called when admin creates a pool.

        Args:
            pool_id:    Your internal pool UUID — used as accountRef
            pool_title: Human readable pool name

        Returns:
            {
                "subaccount_id": str,
                "account_ref":   str,
                "account_name":  str,
            }
        """
        try:
            response = requests.post(
                self.SUBACCOUNTS_URL,
                headers=nomba_client.get_headers(),
                json={
                    "accountName": f"OjaBulk — {pool_title}",
                    "accountRef": str(pool_id),
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Sub-account creation failed: {e}")

        print(f"[DEBUG] create status: {response.status_code}")
        print(f"[DEBUG] create body:   {response.text}")

        if response.status_code not in (200, 201):
            raise PermissionError(
                f"Sub-account creation failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()
        try:
            data = body["data"]
            return {
                "subaccount_id": data["id"],
                "account_ref":   data.get("accountRef", str(pool_id)),
                "account_name":  data.get("accountName", pool_title),
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected response structure: {e}\nFull: {body}"
            )

    def list_subaccounts(self) -> list[dict]:
        """
        Lists all sub-accounts under your parent account.
        """
        try:
            response = requests.get(
                self.SUBACCOUNTS_URL,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"List sub-accounts failed: {e}")

        print(f"[DEBUG] list status: {response.status_code}")
        print(f"[DEBUG] list body:   {response.text}")

        if response.status_code != 200:
            raise PermissionError(
                f"List sub-accounts failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()
        try:
            results = body.get("data", {}).get("results", [])
            return [
                {
                    "subaccount_id": item["id"],
                    "account_name":  item.get("accountName", ""),
                    "account_ref":   item.get("accountRef", ""),
                }
                for item in results
            ]
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected list response: {e}\nFull: {body}"
            )

    def get_subaccount_balance(self, subaccount_id: str) -> dict:
        """
        Fetches real Nomba balance for one pool sub-account.
        Used in reconciliation report.
        """
        url = f"{self.SUBACCOUNTS_URL}/{subaccount_id}/balance"

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Balance fetch failed: {e}")

        print(f"[DEBUG] balance status: {response.status_code}")
        print(f"[DEBUG] balance body:   {response.text}")

        if response.status_code != 200:
            raise PermissionError(
                f"Balance fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        body = response.json()
        try:
            data = body["data"]
            return {
                "subaccount_id":     subaccount_id,
                "available_balance": float(data.get("availableBalance", 0)),
                "ledger_balance":    float(data.get("ledgerBalance", 0)),
            }
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected balance response: {e}\nFull: {body}"
            )

    def verify_against_ledger(
        self,
        subaccount_id: str,
        our_locked_amount: float,
    ) -> dict:
        """
        Compares real Nomba sub-account balance against
        our internal current_locked_amount for one pool.
        """
        balance = self.get_subaccount_balance(subaccount_id)
        nomba_balance = balance["available_balance"]
        discrepancy = abs(nomba_balance - our_locked_amount)

        return {
            "subaccount_id":   subaccount_id,
            "nomba_balance":   nomba_balance,
            "our_ledger":      our_locked_amount,
            "discrepancy":     discrepancy,
            "is_reconciled":   discrepancy == 0.0,
        }


# Single shared instance
sub_account_service = NombaSubAccountService()


if __name__ == "__main__":
    print("Testing NombaSubAccountService...")
    print(f"Using base URL: {NombaSubAccountService.BASE_URL}")
    print(f"Account ID:     {nomba_client.account_id}")

    # Step 1 — list existing sub-accounts
    print("\n--- Listing sub-accounts ---")
    try:
        accounts = sub_account_service.list_subaccounts()
        print(f"Found {len(accounts)} sub-account(s)")
        for acc in accounts:
            print(f"  ref={acc['account_ref']} | name={acc['account_name']} | id={acc['subaccount_id']}")
    except Exception as e:
        print(f"List failed: {e}")

    # Step 2 — create a test sub-account
    print("\n--- Creating test sub-account ---")
    try:
        result = sub_account_service.create_pool_subaccount(
            pool_id="test-pool-ojabulk-001",
            pool_title="Rice Bulk Buy — June 2026",
        )
        print(f"Created successfully:")
        print(f"  subaccount_id: {result['subaccount_id']}")
        print(f"  account_ref:   {result['account_ref']}")
        print(f"  account_name:  {result['account_name']}")

        # Step 3 — fetch balance of new sub-account
        print("\n--- Fetching balance ---")
        balance = sub_account_service.get_subaccount_balance(
            result["subaccount_id"]
        )
        print(f"  Available: ₦{balance['available_balance']:,.2f}")
        print(f"  Ledger:    ₦{balance['ledger_balance']:,.2f}")

        # Step 4 — reconciliation check
        print("\n--- Reconciliation check ---")
        check = sub_account_service.verify_against_ledger(
            subaccount_id=result["subaccount_id"],
            our_locked_amount=0.0,
        )
        print(f"  Nomba balance:  ₦{check['nomba_balance']:,.2f}")
        print(f"  Our ledger:     ₦{check['our_ledger']:,.2f}")
        print(f"  Discrepancy:    ₦{check['discrepancy']:,.2f}")
        print(f"  Reconciled:     {check['is_reconciled']}")

    except Exception as e:
        print(f"Create failed: {e}")