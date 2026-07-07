"""
services/sms.py

SMS notifications via Termii.

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

WHY TERMII:
Robase (a prior provider) sat behind Cloudflare, and server-to-server
calls were being intercepted by a Cloudflare bot-challenge page
(HTTP 403, HTML "Just a moment..." body, Cf-Mitigated: challenge)
before ever reaching Robase's actual backend -- a block on Robase's
side, not fixable from here.

Termii is a solid, Nigeria-focused alternative: account creation and
API key issuance are free (no card required, no upfront deposit) --
you only fund the wallet when you're ready to actually send messages,
and Nigerian SMS is priced per-message in the low-naira range, so a
small top-up comfortably covers a hackathon demo.

OTP generation and verification are handled internally by
services/auth.py and the OTPSession table -- Termii is used ONLY as
the SMS transport layer, never for OTP logic itself.

ENV VARS REQUIRED (already present in core/config.py):
    TERMII_API_KEY  - from your Termii dashboard (Settings > API)
    SMS_SENDER_ID   - REQUIRED, and must be a sender ID already
                       approved for YOUR specific workspace. There is
                       no universal default that works across every
                       Termii account -- "Termii" itself is NOT a
                       usable fallback (confirmed: it returns
                       SENDER_ID_NOT_APPROVED unless your workspace
                       specifically has it whitelisted). In Nigeria,
                       every alphanumeric sender ID needs approval from
                       all four network operators (MTN, Glo, Airtel,
                       9mobile) -- this is an NCC requirement, not a
                       Termii-specific one, so there's no way around it
                       for real alphanumeric-sender delivery.

                       To find out what IS already approved for your
                       account, run:
                           python services/sms.py list-senders
                       This calls Termii's GET /api/sender-id and
                       prints every sender ID on your workspace along
                       with its status ("active" = usable right now).
                       If the list is empty, you'll need to submit one
                       via Termii's dashboard/Sender ID request API and
                       wait for approval (their docs cite 1-5 business
                       days) -- there is no faster alphanumeric path.
"""

import requests

from core.config import settings


class SMSService:

    BASE_URL = "https://v4.api.termii.com/api/sms/send"

    def __init__(self):
        self.api_key = settings.TERMII_API_KEY
        self.sender_id = settings.SMS_SENDER_ID

        if not self.sender_id:
            print(
                "[SMS/Termii] WARNING: SMS_SENDER_ID is not set. There is "
                "no working universal default -- every send will fail "
                "with SENDER_ID_NOT_APPROVED until you set this to a "
                "sender ID actually approved for your workspace. Run "
                "`python services/sms.py list-senders` to see what's "
                "available."
            )

    # ==========================================================
    # Phone normalization
    # ==========================================================

    def _normalize_phone(self, phone: str) -> str:
        """
        Converts Nigerian numbers to the format Termii expects:
        234XXXXXXXXXX (no leading +, no leading 0).

        Examples:
            08012345678     -> 2348012345678
            2348012345678   -> 2348012345678
            +2348012345678  -> 2348012345678
        """
        phone = phone.strip().replace(" ", "").replace("-", "")

        if phone.startswith("+234"):
            return phone[1:]
        if phone.startswith("234"):
            return phone
        if phone.startswith("0"):
            return f"234{phone[1:]}"
        return f"234{phone}"

    # ==========================================================
    # Send
    # ==========================================================

    def _send_sms(self, phone: str, message: str) -> bool:
        """
        Sends SMS via Termii's /sms/send endpoint.

        Returns:
            True if Termii accepted and actually queued the message
            False otherwise

        Never raises -- SMS failure must never crash a request (see
        every call site: reconciliation, payout, refund, and OTP
        request all continue normally even if this returns False,
        since the underlying financial/auth action already succeeded
        by the time the SMS fires).

        NOTE ON "accepted but never arrives":
        Termii can return HTTP 200 while still rejecting the message
        downstream (e.g. an unapproved custom Sender ID on a new
        account). A real success always includes a message_id in the
        response body -- a 200 with no message_id is treated as a
        failure here, not a silent success.
        """
        if not self.api_key:
            print("[SMS/Termii] Missing TERMII_API_KEY")
            return False

        phone = self._normalize_phone(phone)

        payload = {
            "to": phone,
            "from": self.sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": self.api_key,
        }

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
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

        if response.status_code != 200:
            print(
                f"[SMS/Termii] Send failed for {phone} "
                f"[{response.status_code}]: {response.text[:300]}"
            )
            return False

        try:
            body = response.json()
        except ValueError:
            print(f"[SMS/Termii] Non-JSON response for {phone}: {response.text[:300]}")
            return False

        if not body.get("message_id"):
            print(
                f"[SMS/Termii] 200 but no message_id for {phone} -- "
                f"treating as failed. Body: {body}"
            )
            return False

        print(
            f"[SMS/Termii] Sent to {phone} "
            f"(message_id={body.get('message_id')}, balance={body.get('balance')})"
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
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list-senders":
        # Quick diagnostic: which sender IDs (if any) are already
        # approved for THIS workspace/api_key. Run with:
        #   python services/sms.py list-senders
        resp = requests.get(
            "https://v3.api.termii.com/api/sender-id",
            params={"api_key": settings.TERMII_API_KEY},
            timeout=15,
        )
        print(f"Status: {resp.status_code}")
        print(resp.text)
        sys.exit(0)

    print("Testing Termii SMS Service...")

    test_phone = os.getenv("SMS_TEST_PHONE", "")

    if not test_phone:
        print("Set SMS_TEST_PHONE in your .env file.")
    else:
        print(f"Sending OTP to {test_phone}...")
        result = sms_service.send_otp_code(phone=test_phone, code="123456")
        print(f"Success: {result}")
