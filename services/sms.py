"""
services/sms.py

SMS notifications via Gideon's Technology SMS API.

Supported messages (unchanged -- every call site elsewhere in the
codebase, e.g. services/auth.py, engine/payout.py, engine/refund.py,
engine/reconciliation.py, routers/traders.py, keeps working with zero
changes, since these method names/signatures are the stable public
interface of this module):
1. Virtual account created
2. Payment received
3. Pool fulfilled / payout processing
4. Pool refunded
5. Login OTP
6. Esusu payout / payout processing

WHY GIDEON'S TECHNOLOGY:
Every previous attempt (Robase, Termii, Africa's Talking sandbox) got
blocked by the same wall: Nigeria's NCC requires an approved sender ID
before an alphanumeric-branded text will actually deliver, and that
approval can take days. Gideon's Technology's API is used here WITHOUT
setting a custom senderId at all -- their documented success response
shows "provider": "africastalking", meaning they're a reseller
wrapping Africa's Talking's infrastructure, and omitting senderId
falls through to whatever default they route through, sidestepping
the same-day approval wait. Their dashboard also mentions free trial
credits (trialRemaining in the response), useful for testing before
committing spend.

OTP generation and verification are handled internally by
services/auth.py and the OTPSession table -- this file is used ONLY
as the SMS transport layer, never for OTP logic itself.

ENV VARS REQUIRED (already present in core/config.py):
    GIDEONS_SMS_API_KEY - from your Gideons Technology dashboard
"""

import requests

from core.config import settings


class SMSService:

    BASE_URL = "https://gideonstechnology.com/api/customer/sms/send"

    def __init__(self):
        self.api_key = settings.GIDEONS_SMS_API_KEY

    # ==========================================================
    # Phone normalization
    # ==========================================================

    def _normalize_phone(self, phone: str) -> str:
        """
        Converts Nigerian numbers to E.164 format (+234XXXXXXXXXX),
        which is what Gideon's Technology's API expects for `to`.

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
        Sends SMS via Gideon's Technology's /sms/send endpoint.

        Returns:
            True if the API reports success: true
            False otherwise

        Never raises -- SMS failure must never crash a request (see
        every call site: reconciliation, payout, refund, and OTP
        request all continue normally even if this returns False,
        since the underlying financial/auth action already succeeded
        by the time the SMS fires).

        NOTE: senderId is deliberately omitted from the payload -- see
        this file's module docstring for why (avoids the NCC sender-ID
        approval wait by falling through to their default routing).
        """
        if not self.api_key:
            print("[SMS/Gideons] Missing GIDEONS_SMS_API_KEY")
            return False

        phone = self._normalize_phone(phone)

        payload = {
            "to": phone,
            "message": message,
        }

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            print(f"[SMS/Gideons] Timeout sending to {phone}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"[SMS/Gideons] Connection error for {phone}: {e}")
            return False
        except Exception as e:
            print(f"[SMS/Gideons] Exception for {phone}: {e}")
            return False

        try:
            body = response.json()
        except ValueError:
            print(f"[SMS/Gideons] Non-JSON response for {phone}: {response.text[:300]}")
            return False

        if response.status_code != 200 or not body.get("success"):
            print(
                f"[SMS/Gideons] Send failed for {phone} "
                f"[{response.status_code}]: {body.get('error', body)}"
            )
            if "balance" in body and "required" in body:
                print(
                    f"[SMS/Gideons] Balance too low: have {body.get('balance')}, "
                    f"need {body.get('required')} -- top up the account."
                )
            return False

        print(
            f"[SMS/Gideons] Sent to {phone} "
            f"(messageId={body.get('messageId')}, "
            f"balance={body.get('balance')}, "
            f"provider={body.get('provider')})"
        )
        return True

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
    # POOL PAYOUT PROCESSING (transfer accepted, not yet confirmed)
    # ==========================================================

    def send_pool_payout_processing(
        self,
        phone: str,
        trader_name: str,
        pool_title: str,
        supplier_name: str,
    ) -> bool:
        message = (
            f"OjaBulk: {pool_title} reached its target!\n"
            f"Payment to {supplier_name} is processing.\n"
            f"We'll confirm once Nomba settles the transfer."
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

    # ==========================================================
    # ESUSU PAYOUT PROCESSING (real bank transfer accepted, not yet confirmed)
    # ==========================================================

    def send_esusu_payout_processing(
        self,
        phone: str,
        trader_name: str,
        amount: float,
        round_number: int,
    ) -> bool:
        first_name = trader_name.split()[0]
        message = (
            f"OjaBulk: Congrats {first_name}!\n"
            f"Your N{amount:,.0f} Esusu payout (round {round_number}) "
            f"is processing to your bank account.\n"
            f"We'll confirm once Nomba settles it."
        )
        return self._send_sms(phone, message)

    # ==========================================================
    # ESUSU PAYOUT
    # ==========================================================

    def send_esusu_payout(
        self,
        phone: str,
        trader_name: str,
        amount: float,
        round_number: int,
    ) -> bool:
        first_name = trader_name.split()[0]
        message = (
            f"OjaBulk: Congrats {first_name}!\n"
            f"You received N{amount:,.0f} as this round's "
            f"Esusu beneficiary (round {round_number}).\n"
            f"Added to your spendable balance."
        )
        return self._send_sms(phone, message)


# Shared singleton instance
sms_service = SMSService()


if __name__ == "__main__":
    import os

    print("Testing Gideon's Technology SMS Service...")

    test_phone = os.getenv("SMS_TEST_PHONE", "")

    if not test_phone:
        print("Set SMS_TEST_PHONE in your .env file.")
    else:
        print(f"Sending OTP to {test_phone}...")
        result = sms_service.send_otp_code(phone=test_phone, code="123456")
        print(f"Success: {result}")
