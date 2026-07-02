import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()


class NombaClient:
    """
    Handles Nomba API authentication using OAuth 2.0 client_credentials.
    - Issues token via /auth/token/issue
    - Refreshes via /auth/token/refresh at 55-minute mark
    - Caches token in memory (sufficient for hackathon; use Redis in production)
    """

    BASE_URL = os.getenv("NOMBA_BASE_URL", "https://sandbox.nomba.com")
    TOKEN_ISSUE_URL = f"{BASE_URL}/auth/token/issue"
    TOKEN_REFRESH_URL = f"{BASE_URL}/auth/token/refresh"

    def __init__(self):
        self.account_id = os.getenv("NOMBA_ACCOUNT_ID")
        self.client_id = os.getenv("TEST_CLIENT_ID")
        self.client_secret = os.getenv("TEST_CLIENT_SECRET")
        self.subaccount_id = os.getenv("NOMBA_SUB_ACCOUNT_ID")
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None

        self._validate_env()

    def _validate_env(self):
        missing = [
            key for key, val in {
                "NOMBA_ACCOUNT_ID": self.account_id,
                "NOMBA_SUB_ACCOUNT_ID": self.subaccount_id,
                "TEST_CLIENT_ID": self.client_id,
                "TEST_CLIENT_SECRET": self.client_secret,
            }.items() if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def _now(self) -> datetime:
        """Timezone-aware current UTC time."""
        return datetime.now(timezone.utc)

    def _is_token_valid(self) -> bool:
        if not self._access_token or not self._token_expires_at:
            return False
        return self._now() < (self._token_expires_at - timedelta(minutes=5))

    def _parse_token_response(self, body: dict):
        try:
            token_data = body["data"]
            self._access_token = token_data["access_token"]
            self._refresh_token = token_data.get("refresh_token")
            expires_in = int(token_data.get("expires_in", 3600))
            self._token_expires_at = self._now() + timedelta(seconds=expires_in)
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Unexpected Nomba token response: {e}\nFull body: {body}"
            )

    def _issue_token(self):
        try:
            response = requests.post(
                self.TOKEN_ISSUE_URL,
                headers={
                    "Content-Type": "application/json",
                    "accountId": self.account_id,
                },
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Nomba token issue request failed: {e}")

        if response.status_code != 200:
            raise PermissionError(
                f"Nomba auth failed [{response.status_code}]: {response.text}"
            )

        self._parse_token_response(response.json())

    def _refresh_token_request(self):
        if not self._refresh_token:
            self._issue_token()
            return

        try:
            response = requests.post(
                self.TOKEN_REFRESH_URL,
                headers={
                    "Content-Type": "application/json",
                    "accountId": self.account_id,
                },
                json={
                    "refresh_token": self._refresh_token,
                },
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            print(f"[NombaClient] Refresh request failed: {e}. Re-issuing token.")
            self._issue_token()
            return

        if response.status_code != 200:
            print(
                f"[NombaClient] Refresh failed [{response.status_code}]. "
                f"Re-issuing token."
            )
            self._issue_token()
            return

        self._parse_token_response(response.json())

    def get_token(self) -> str:
        if not self._access_token:
            self._issue_token()
        elif not self._is_token_valid():
            self._refresh_token_request()
        return self._access_token

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json",
            "accountId": self.account_id,
        }


# Single shared instance — import this everywhere
nomba_client = NombaClient()


if __name__ == "__main__":
    print("Testing Nomba authentication...")
    try:
        headers = nomba_client.get_headers()
        print("Token issued successfully")
        print(f"Token preview: {headers['Authorization'][:30]}...")
        print(f"Expires at (UTC): {nomba_client._token_expires_at}")
        print(f"Refresh token present: {bool(nomba_client._refresh_token)}")
    except Exception as e:
        print(f"Auth failed: {e}")