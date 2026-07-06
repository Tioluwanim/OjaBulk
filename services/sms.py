"""
services/sms.py

SMS notifications via Robase.

Supported messages:
1. Virtual account created
2. Payment received
3. Pool fulfilled
4. Pool refunded
5. Login OTP

IMPORTANT:

OTP generation and verification are handled internally by
services/auth.py and the OTPSession table.

Robase is used only as the SMS transport layer.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()


class SMSService:
    BASE_URL = "https://api.robase.dev/v1"

    def __init__(self):
        self.api_key = os.getenv("ROBASE_API_KEY", "").strip()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OjaBulk/1.0",
        }

    def _normalize_phone(self, phone: str) -> str:
        """
        Converts Nigerian numbers to E.164 format.

        Examples:
            08012345678     -> +2348012345678
            2348012345678   -> +2348012345678
            +2348012345678  -> +2348012345678
        """
        phone = (
            phone.strip()
            .replace(" ", "")
            .replace("-", "")
        )

        if phone.startswith("+234"):
            return phone

        if phone.startswith("234"):
            return f"+{phone}"

        if phone.startswith("0"):
            return f"+234{phone[1:]}"

        return f"+234{phone}"

    def _send_sms(
            self,
            phone: str,
            message: str,
    ) -> bool:
        """
        Sends SMS via Robase.

        Returns:
            True if accepted by Robase
            False otherwise
        """
        if not self.api_key:
            print("[SMS] Missing ROBASE_API_KEY")
            return False

        phone = self._normalize_phone(phone)

        payload = {
            "phone_number": phone,
            "message": message,
            "metadata": {
                "app": "OjaBulk"
            }
        }

        url = f"{self.BASE_URL}/sms/send"

        try:
            # Debug info
            print("\n" + "=" * 60)
            print("[SMS] Sending SMS")
            print(f"URL: {url}")
            print(f"Phone: {phone}")
            print(f"API Key Loaded: {'YES' if self.api_key else 'NO'}")
            print(f"API Key Prefix: {self.api_key[:10]}...")
            print(f"Payload: {payload}")
            print("=" * 60)

            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=15,
            )

            print("\n" + "=" * 60)
            print("[SMS] Response")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text[:2000]}")
            print("=" * 60)

            if response.status_code in (200, 201):
                print(f"[SMS] Successfully sent to {phone}")
                return True

            print(
                f"[SMS] Send failed for {phone} "
                f"[{response.status_code}]"
            )

            return False

        except requests.exceptions.Timeout:
            print(f"[SMS] Timeout while sending to {phone}")
            return False

        except requests.exceptions.ConnectionError as e:
            print(f"[SMS] Connection error for {phone}: {e}")
            return False

        except Exception as e:
            print(f"[SMS] Exception for {phone}: {e}")
            return False

    # ==========================================================
    # OTP
    # ==========================================================

    def send_otp_code(
        self,
        phone: str,
        code: str,
    ) -> bool:
        """
        Sends an OTP generated internally by OjaBulk.

        NOTE:
        auth.py generates and verifies OTPs.
        Robase only delivers the SMS.
        """
        message = (
            f"OjaBulk login code: {code}\n"
            f"Valid for 10 minutes.\n"
            f"Do not share this code with anyone."
        )

        return self._send_sms(phone, message)

    # ==========================================================
    # ACCOUNT CREATED
    # ==========================================================

    def send_account_created(
        self,
        phone: str,
        trader_name: str,
        account_number: str,
        bank_name: str,
    ) -> bool:
        first_name = trader_name.split()[0]

        message = (
            f"Welcome to OjaBulk, {first_name}!\n"
            f"Your account: {account_number} — {bank_name}\n"
            f"Send money here to contribute to your pool."
        )

        return self._send_sms(phone, message)

    # ==========================================================
    # PAYMENT RECEIVED
    # ==========================================================

    def send_payment_received(
        self,
        phone: str,
        trader_name: str,
        total_amount: float,
        pool_cut: float,
        spendable_cut: float,
        pool_name: str | None,
        pool_progress_pct: float | None,
    ) -> bool:
        first_name = trader_name.split()[0]

        if pool_cut > 0 and pool_name:
            progress_text = (
                f" Pool: {pool_progress_pct:.0f}% complete."
                if pool_progress_pct is not None
                else ""
            )

            message = (
                f"OjaBulk: ₦{total_amount:,.0f} received.\n"
                f"₦{pool_cut:,.0f} locked in {pool_name}.\n"
                f"₦{spendable_cut:,.0f} added to spendable."
                f"{progress_text}"
            )
        else:
            message = (
                f"OjaBulk: ₦{total_amount:,.0f} received, "
                f"{first_name}.\n"
                f"Added to your spendable balance.\n"
                f"Join a pool to start contributing toward wholesale."
            )

        return self._send_sms(phone, message)

    # ==========================================================
    # POOL FULFILLED
    # ==========================================================

    def send_pool_fulfilled(
        self,
        phone: str,
        trader_name: str,
        pool_title: str,
        contribution_amount: float,
        supplier_name: str,
    ) -> bool:
        message = (
            f"OjaBulk: {pool_title} reached its target!\n"
            f"Payment sent to {supplier_name}.\n"
            f"Your contribution: ₦{contribution_amount:,.0f} confirmed.\n"
            f"Una pool don full!"
        )

        return self._send_sms(phone, message)

    # ==========================================================
    # POOL REFUNDED
    # ==========================================================

    def send_pool_refunded(
        self,
        phone: str,
        trader_name: str,
        pool_title: str,
        refund_amount: float,
    ) -> bool:
        message = (
            f"OjaBulk: {pool_title} did not reach its target.\n"
            f"₦{refund_amount:,.0f} returned to your spendable balance.\n"
            f"No wahala — your money is safe."
        )

        return self._send_sms(phone, message)


# Shared singleton instance
sms_service = SMSService()


if __name__ == "__main__":
    print("Testing Robase SMS Service...")

    test_phone = os.getenv("SMS_TEST_PHONE", "")

    if not test_phone:
        print("Set SMS_TEST_PHONE in your .env file.")
    else:
        print(f"Sending OTP to {test_phone}...")

        result = sms_service.send_otp_code(
            phone=test_phone,
            code="123456",
        )

        print(f"Success: {result}")