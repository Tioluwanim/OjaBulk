import os
import requests

from services.client import nomba_client


class NombaVirtualAccountService:

    BASE_URL = os.getenv(
        "NOMBA_BASE_URL",
        "https://sandbox.nomba.com/v1"
    ).rstrip("/")

    SUBACCOUNT_ID = os.getenv(
        "NOMBA_SUB_ACCOUNT_ID"
    )

    def create(
        self,
        trader_id: str,
        trader_name: str,
        callback_url: str | None = None,
    ) -> dict:
        """
        Create a virtual account under the configured sub-account.
        """

        if not self.SUBACCOUNT_ID:
            raise EnvironmentError(
                "NOMBA_SUB_ACCOUNT_ID is required"
            )

        url = (
            f"{self.BASE_URL}"
            f"/accounts/virtual/{self.SUBACCOUNT_ID}"
        )

        payload = {
            "accountRef": str(trader_id),
            "accountName": trader_name,
        }

        if callback_url:
            payload["callbackUrl"] = callback_url

        try:
            response = requests.post(
                url,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=15,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Virtual account creation failed: {e}"
            )

        if response.status_code == 409:
            return self.fetch(trader_id)

        if response.status_code not in (200, 201):
            raise PermissionError(
                f"Virtual account creation failed "
                f"[{response.status_code}]: {response.text}"
            )

        return self._parse_response(
            response.json()
        )

    def fetch(self, identifier: str) -> dict:
        """
        Fetch virtual account by identifier.
        """

        url = (
            f"{self.BASE_URL}"
            f"/accounts/virtual/{identifier}"
        )

        try:
            response = requests.get(
                url,
                headers=nomba_client.get_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Virtual account fetch failed: {e}"
            )

        if response.status_code == 404:
            raise ValueError(
                f"No virtual account found "
                f"for identifier={identifier}"
            )

        if response.status_code != 200:
            raise PermissionError(
                f"Virtual account fetch failed "
                f"[{response.status_code}]: {response.text}"
            )

        return self._parse_response(
            response.json()
        )

    def list_accounts(
        self,
        limit: int = 20,
    ) -> dict:
        """
        List virtual accounts.
        """

        url = (
            f"{self.BASE_URL}"
            f"/accounts/virtual/list"
        )

        payload = {
            "limit": limit
        }

        try:
            response = requests.post(
                url,
                headers=nomba_client.get_headers(),
                json=payload,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Virtual account list failed: {e}"
            )

        if response.status_code != 200:
            raise PermissionError(
                f"Virtual account list failed "
                f"[{response.status_code}]: {response.text}"
            )

        return response.json()

    def _parse_response(
        self,
        body: dict
    ) -> dict:

        data = body.get("data", {})

        return {
            "account_ref": data.get("accountRef"),
            "bank_name": data.get("bankName"),
            "bank_account_number": data.get(
                "bankAccountNumber"
            ),
            "bank_account_name": data.get(
                "bankAccountName"
            ),
            "currency": data.get(
                "currency",
                "NGN"
            ),
        }


virtual_account_service = (
    NombaVirtualAccountService()
)


if __name__ == "__main__":

    import uuid

    print(
        "Testing NombaVirtualAccountService..."
    )

    trader_id = str(uuid.uuid4())

    try:
        result = (
            virtual_account_service.create(
                trader_id=trader_id,
                trader_name="Emeka Okafor Test",
            )
        )

        print("\nCreated VA")
        print(result)

        print("\nListing VAs")
        print(
            virtual_account_service.list_accounts()
        )

    except Exception as e:
        print(f"Test failed: {e}")