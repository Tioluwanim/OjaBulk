"""
services/sms.py

SMS notifications via Africa's Talking.

Supported messages (unchanged -- every call site elsewhere in the
codebase, e.g. services/auth.py, engine/payout.py, engine/refund.py,
engine/reconciliation.py, routers/traders.py, keeps working with zero
changes, since these five method names/signatures are the stable
public interface of this module):
1. Virtual account created
2. Payment received
3. Pool fulfilled
4. Pool refunded
5. Login OTP

WHY AFRICA'S TALKING:
Robase (a prior provider) sat behind Cloudflare, and server-to-server
calls were being intercepted by a Cloudflare bot-challenge page
(HTTP 403, HTML "Just a moment..." body, Cf-Mitigated: challenge)
before ever reaching Robase's actual backend -- a block on Robase's
side, not fixable from here.

Africa's Talking is used instead because this app already has an
approved Africa's Talking account and live credentials wired for the
USSD menu (see routers/ussd.py, services/ussd.py) -- AFRICAS_TALKING_API_KEY
and AFRICAS_TALKING_USERNAME in core/config.py. SMS runs on the same
account/credentials, so no new signup, no new sender-ID approval wait.

OTP generation and verification are handled internally by
services/auth.py and the OTPSession table -- Africa's Talking is used
ONLY as the SMS transport layer, never for OTP logic itself.

ENV VARS REQUIRED (already present in core/config.py):
    AFRICAS_TALKING_API_KEY   - from the Africa's Talking dashboard
    AFRICAS_TALKING_USERNAME  - your AT app username, or "sandbox" for
                                 the free sandbox app (sandbox messages
                                 are simulated -- they don't reach a
                                 real handset, but let you verify the
                                 integration end-to-end before your
                                 live username/sender ID is approved)
    SMS_SENDER_ID              - optional registered short code / alpha
                                 sender ID. Leave unset to send from
                                 AT's shared default while an alpha
                                 sender ID is pending approval.
"""

import requests

from core.config import settings


class SMSService:

    PRODUCTION_URL = "https://api.africastalking.com/version1/messaging"
    SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"

    def __init__(self):
        self.api_key = settings.AFRICAS_TALKING_API_KEY
        self.username = "radet"

        # Africa's Talking routes "sandbox" username to a separate
        # simulated environment -- anything else is treated as a real
        # live app username against the production endpoint.
        self.base_url = (
            self.SANDBOX_URL if self.username == "sandbox" else self.PRODUCTION_URL
        )

    # ==========================================================
    # Phone normalization
    # ==========================================================

    def _normalize_phone(self, phone: str) -> str:
        """
        Converts Nigerian numbers to E.164 format, which is what
        Africa's Talking expects in the "to" field.

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
    # Send
    # ==========================================================

    def _send_sms(self, phone: str, message: str) -> bool:
        """
        Sends SMS via Africa's Talking's /messaging endpoint.

        Returns:
            True if AT accepted the message for at least one recipient
            False otherwise

        Never raises -- SMS failure must never crash a request (see
        every call site: reconciliation, payout, refund, and OTP
        request all continue normally even if this returns False,
        since the underlying financial/auth action already succeeded
        by the time the SMS fires).
        """
        if not self.api_key or not self.username:
            print("[SMS] Missing AFRICAS_TALKING_API_KEY or AFRICAS_TALKING_USERNAME")
            return False

        phone = self._normalize_phone(phone)

        headers = {
            "apiKey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "username": self.username,
            "to": phone,
            "message": message,
        }
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                data=data,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            print(f"[SMS/AfricasTalking] Timeout sending to {phone}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"[SMS/AfricasTalking] Connection error for {phone}: {e}")
            return False
        except Exception as e:
            print(f"[SMS/AfricasTalking] Exception for {phone}: {e}")
            return False

        if response.status_code not in (200, 201):
            print(
                f"[SMS/AfricasTalking] Send failed for {phone} "
                f"[{response.status_code}]: {response.text[:300]}"
            )
            return False

        try:
            body = response.json()
        except ValueError:
            print(
                f"[SMS/AfricasTalking] Non-JSON response for {phone}: "
                f"{response.text[:300]}"
            )
            return False

        recipients = (
            body.get("SMSMessageData", {}).get("Recipients", [])
        )

        if not recipients:
            print(
                f"[SMS/AfricasTalking] No recipients in response for "
                f"{phone}. Body: {body}"
            )
            return False

        # AT returns per-recipient status, e.g. "Success" or a specific
        # rejection reason (bad number, insufficient balance, sender ID
        # not allowed, etc). Treat anything other than "Success" as a
        # failure for that recipient.
        recipient = recipients[0]
        status = recipient.get("status", "")

        if status == "Success":
            print(
                f"[SMS/AfricasTalking] Sent to {phone} "
                f"(messageId={recipient.get('messageId')}, "
                f"cost={recipient.get('cost')})"
            )
            return True

        print(
            f"[SMS/AfricasTalking] Rejected for {phone}: "
            f"status={status}, statusCode={recipient.get('statusCode')}"
        )
        return False

    # ==========================================================
    # OTP
    # ==========================================================

    def send_otp_code(self, phone: str, code: str) -> bool:
        """
        Sends an OTP generated internally by OjaBulk.
        auth.py generates and verifies OTPs -- this only delivers the SMS.
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
            f"Your account: {account_number} -- {bank_name}\n"
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
                f"OjaBulk: N{total_amount:,.0f} received.\n"
                f"N{pool_cut:,.0f} locked in {pool_name}.\n"
                f"N{spendable_cut:,.0f} added to spendable."
                f"{progress_text}"
            )
        else:
            message = (
                f"OjaBulk: N{total_amount:,.0f} received, "
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
            f"Your contribution: N{contribution_amount:,.0f} confirmed.\n"
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
            f"N{refund_amount:,.0f} returned to your spendable balance.\n"
            f"No wahala -- your money is safe."
        )
        return self._send_sms(phone, message)


# Shared singleton instance
sms_service = SMSService()


if __name__ == "__main__":
    import os

    print(f"Testing Africa's Talking SMS Service (username: {sms_service.username})...")

    test_phone = os.getenv("SMS_TEST_PHONE", "")

    if not test_phone:
        print("Set SMS_TEST_PHONE in your .env file.")
    else:
        print(f"Sending OTP to {test_phone}...")
        result = sms_service.send_otp_code(phone=test_phone, code="123456")
        print(f"Success: {result}")
