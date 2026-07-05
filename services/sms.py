"""
services/sms.py

SMS notifications via Termii (Nigerian-focused) with Resend fallback.

Four SMS types only:
1. Virtual account created
2. Payment received (with split breakdown)
3. Pool fulfilled (supplier paid)
4. Pool refunded (deadline missed)
"""

import requests
import os


class SMSService:

    def __init__(self):
        self.termii_api_key = os.getenv("TERMII_API_KEY", "")
        self.termii_url = "https://api.ng.termii.com/api/sms/send"
        self.sender_id = os.getenv("SMS_SENDER_ID", "OjaBulk")

    def _send(self, phone: str, message: str) -> bool:
        """
        Sends an SMS via Termii.
        Returns True on success, False on failure (non-blocking — SMS failure
        should never crash the reconciliation engine).
        """
        if not self.termii_api_key:
            print(f"[SMS] No API key — would send to {phone}: {message}")
            return False

        # Normalize Nigerian phone number to international format
        phone = self._normalize_phone(phone)

        payload = {
            "to":      phone,
            "from":    self.sender_id,
            "sms":     message,
            "type":    "plain",
            "channel": "generic",
            "api_key": self.termii_api_key,
        }

        try:
            response = requests.post(
                self.termii_url,
                json=payload,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[SMS] Send failed for {phone}: {e}")
            return False

    def _normalize_phone(self, phone: str) -> str:
        """Converts 08012345678 → 2348012345678"""
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "234" + phone[1:]
        if not phone.startswith("234"):
            phone = "234" + phone
        return phone

    def send_account_created(
        self,
        phone: str,
        trader_name: str,
        account_number: str,
        bank_name: str,
    ) -> bool:
        message = (
            f"Welcome to OjaBulk, {trader_name.split()[0]}!\n"
            f"Your account: {account_number} — {bank_name}\n"
            f"Send money here to contribute to your pool. Any bank, anytime."
        )
        return self._send(phone, message)

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
        name = trader_name.split()[0]

        if pool_cut > 0 and pool_name:
            progress_text = (
                f" Pool: {pool_progress_pct:.0f}% complete."
                if pool_progress_pct is not None else ""
            )
            message = (
                f"OjaBulk: \u20a6{total_amount:,.0f} received.\n"
                f"\u20a6{pool_cut:,.0f} locked in {pool_name}.\n"
                f"\u20a6{spendable_cut:,.0f} added to spendable.{progress_text}"
            )
        else:
            message = (
                f"OjaBulk: \u20a6{total_amount:,.0f} received, {name}.\n"
                f"Added to your spendable balance.\n"
                f"Join a pool to start contributing toward wholesale."
            )

        return self._send(phone, message)

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
            f"Your contribution: \u20a6{contribution_amount:,.0f} confirmed. "
            f"Una pool don full!"
        )
        return self._send(phone, message)

    def send_pool_refunded(
        self,
        phone: str,
        trader_name: str,
        pool_title: str,
        refund_amount: float,
    ) -> bool:
        message = (
            f"OjaBulk: {pool_title} did not reach its target.\n"
            f"\u20a6{refund_amount:,.0f} returned to your spendable balance.\n"
            f"No wahala — your money is safe."
        )
        return self._send(phone, message)

    def send_otp_code(
        self,
        phone: str,
        code: str,
    ) -> bool:
        """
        Sends a login OTP code. Used by services/auth.py for all three
        login roles (trader, head_of_traders, wholesaler) — the OTP
        flow itself is identical regardless of role.
        """
        message = (
            f"OjaBulk login code: {code}\n"
            f"Valid for 10 minutes. Do not share this code with anyone."
        )
        return self._send(phone, message)


# Single shared instance
sms_service = SMSService()
