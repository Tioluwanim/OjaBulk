"""
services/sms.py

SMS notifications with a swappable provider underneath.

Supported messages (unchanged — every call site elsewhere in the
codebase, e.g. services/auth.py, engine/payout.py, engine/refund.py,
engine/reconciliation.py, routers/traders.py, keeps working with zero
changes, since these five method names/signatures are the stable
public interface of this module):
1. Virtual account created
2. Payment received
3. Pool fulfilled
4. Pool refunded
5. Login OTP

PROVIDER SWITCH — why this exists:
    Robase (the previous provider) started returning Cloudflare
    bot-challenge pages (HTML "Just a moment...", HTTP 403,
    Cf-Mitigated: challenge) instead of real API responses on their
    SMS endpoint — a misconfiguration on Robase's side, not fixable
    from this codebase. Switched to Arkesel as the primary provider.

    Termii credentials are still read and wired as a same-day
    fallback: set SMS_PROVIDER=termii in .env and every message keeps
    working with zero code changes, in case Arkesel hits any snag
    (sender-ID approval delay, unexpected payload behavior for
    Nigerian +234 numbers specifically — every confirmed Arkesel code
    sample found during integration used Ghanaian 233... numbers, so
    this is the one thing to verify with a real test send before
    relying on it for a live demo) before the actual presentation.

    core/config.py's SMS_PROVIDER setting picks which one is active.

OTP generation and verification are handled internally by
services/auth.py and the OTPSession table — every provider here is
used ONLY as the SMS transport layer, never for OTP logic itself.
"""

import requests

from core.config import settings


class SMSService:

    ARKESEL_URL = "https://sms.arkesel.com/api/v2/sms/send"
    TERMII_URL = "https://api.ng.termii.com/api/sms/send"

    def __init__(self):
        self.provider = settings.SMS_PROVIDER
        self.sender_id = settings.SMS_SENDER_ID
        self.arkesel_api_key = settings.ARKESEL_API_KEY
        self.termii_api_key = settings.TERMII_API_KEY

    # ==========================================================
    # Phone normalization
    # ==========================================================

    def _normalize_phone(self, phone: str) -> str:
        """
        Converts Nigerian numbers to E.164 format.

        Examples:
            08012345678     -> +2348012345678
            2348012345678   -> +2348012345678
            +2348012345678  -> +2348012345678
        """
        phone = phone.strip().replace(" ", "").replace("-", "")

        if phone.startswith("+234"):
            return phone
        if phone.startswith("234"):
            return f"+{phone}"
        if phone.startswith("0"):
            return f"+234{phone[1:]}"
        return f"+234{phone}"

    # ==========================================================
    # Provider dispatch
    # ==========================================================

    def _send_sms(self, phone: str, message: str) -> bool:
        """
        Sends SMS via whichever provider is active in
        settings.SMS_PROVIDER. Returns True if the provider accepted
        the message, False otherwise. Never raises — SMS failure must
        never crash a request (see every call site: reconciliation,
        payout, refund, and OTP request all continue normally even if
        this returns False, since the underlying financial/auth action
        already succeeded by the time the SMS fires).
        """
        phone = self._normalize_phone(phone)

        if self.provider == "termii":
            return self._send_via_termii(phone, message)

        # Default / anything else configured falls through to Arkesel,
        # matching settings.SMS_PROVIDER's own default of "arkesel".
        return self._send_via_arkesel(phone, message)

    def _send_via_arkesel(self, phone: str, message: str) -> bool:
        if not self.arkesel_api_key:
            print("[SMS] Missing ARKESEL_API_KEY")
            return False

        headers = {
            "api-key": self.arkesel_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "sender": self.sender_id[:11],  # Arkesel caps sender ID at 11 chars
            "message": message,
            "recipients": [phone],
        }

        try:
            response = requests.post(
                self.ARKESEL_URL,
                headers=headers,
                json=payload,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            print(f"[SMS/Arkesel] Timeout sending to {phone}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"[SMS/Arkesel] Connection error for {phone}: {e}")
            return False
        except Exception as e:
            print(f"[SMS/Arkesel] Exception for {phone}: {e}")
            return False

        if response.status_code == 200:
            print(f"[SMS/Arkesel] Sent to {phone}")
            return True

        print(
            f"[SMS/Arkesel] Send failed for {phone} "
            f"[{response.status_code}]: {response.text[:300]}"
        )
        return False

    def _send_via_termii(self, phone: str, message: str) -> bool:
        if not self.termii_api_key:
            print("[SMS/Termii] Missing TERMII_API_KEY")
            return False

        payload = {
            "to": phone,
            "from": self.sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": self.termii_api_key,
        }

        try:
            response = requests.post(
                self.TERMII_URL,
                json=payload,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            print(f"[SMS/Termii] Timeout sending to {phone}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"[SMS/Termii] Connection error for {phone}: {e}")
            return False
        except Exception as e:
            print(f"[SMS/Termii] Exception for {phone}: {e}")
            return False

        if response.status_code == 200:
            print(f"[SMS/Termii] Sent to {phone}")
            return True

        print(
            f"[SMS/Termii] Send failed for {phone} "
            f"[{response.status_code}]: {response.text[:300]}"
        )
        return False

    # ==========================================================
    # OTP
    # ==========================================================

    def send_otp_code(self, phone: str, code: str) -> bool:
        """
        Sends an OTP generated internally by OjaBulk.
        auth.py generates and verifies OTPs — this only delivers the SMS.
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
    import os

    print(f"Testing SMS Service (provider: {sms_service.provider})...")

    test_phone = os.getenv("SMS_TEST_PHONE", "")

    if not test_phone:
        print("Set SMS_TEST_PHONE in your .env file.")
    else:
        print(f"Sending OTP to {test_phone} via {sms_service.provider}...")
        result = sms_service.send_otp_code(phone=test_phone, code="123456")
        print(f"Success: {result}")