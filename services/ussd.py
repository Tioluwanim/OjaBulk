"""
services/ussd.py

Africa's Talking USSD session handler — read-only balance and pool status.

Scope is deliberately narrow:
- Balance check (spendable + locked)
- Active pool status (name, progress, deadline)
- No payments, no joining pools, no state changes over USSD

USSD response rules:
- CON prefix = session continues (show menu, expect more input)
- END prefix = session terminates (final response)
- Max ~160 chars per response
- Identity = phone number (no login, read-only so acceptable)
"""


class USSDService:

    # Africa's Talking / most carriers cap a single USSD screen around
    # 160-182 chars depending on network. Leaving the raw, unbounded
    # pool.title to interpolate directly (previous behavior) meant a
    # long title could silently truncate the deadline line off the end
    # of the message, or in some carrier implementations return an
    # error instead of a truncated screen. Cap it well under the
    # tightest known limit so the rest of the screen always survives.
    MAX_TITLE_LENGTH = 40

    def _truncate(self, text: str, max_length: int) -> str:
        if text is None:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "\u2026"

    def handle_session(
        self,
        session_id: str,
        phone_number: str,
        text: str,
        get_trader_by_phone,   # callable injected from router
    ) -> str:
        """
        Processes one USSD session step.

        Args:
            session_id:          Africa's Talking session ID
            phone_number:        Caller's phone (identity for trader lookup)
            text:                Cumulative input so far (empty on first dial)
            get_trader_by_phone: DB lookup function injected from the router
                                 Signature: (phone: str) -> Trader | None

        Returns:
            String starting with CON (continue) or END (terminate)
        """
        trader = get_trader_by_phone(phone_number)

        # First dial — show main menu
        if text == "":
            return self._main_menu(trader)

        # Option 1 — balances
        if text == "1":
            return self._balance_screen(trader)

        # Option 2 — pool status
        if text == "2":
            return self._pool_status_screen(trader)

        # Exit
        if text == "0":
            return "END Thank you for using OjaBulk."

        # Unrecognised input
        return "END Invalid option. Please dial again and choose 1 or 2."

    def _main_menu(self, trader) -> str:
        if trader is None:
            return (
                "END You are not registered on OjaBulk.\n"
                "Contact your market association to register."
            )
        name = trader.name.split()[0]
        return (
            f"CON Welcome, {name}!\n"
            f"1. My balances\n"
            f"2. My pool status\n"
            f"0. Exit"
        )

    def _balance_screen(self, trader) -> str:
        if trader is None:
            return "END No account found for this number."
        return (
            f"END OjaBulk Balances:\n"
            f"Spendable: \u20a6{trader.spendable_balance:,.0f}\n"
            f"Locked in pools: \u20a6{self._get_total_locked(trader):,.0f}"
        )

    def _pool_status_screen(self, trader) -> str:
        if trader is None:
            return "END No account found for this number."

        active_pool = self._get_active_pool(trader)
        if active_pool is None:
            return (
                "END You have no active pool.\n"
                "Visit ojabulk.com to join a pool."
            )

        progress = 0.0
        if active_pool.target_amount > 0:
            progress = (active_pool.current_locked_amount / active_pool.target_amount) * 100

        deadline_str = active_pool.deadline.strftime("%d %b %Y")

        return (
            f"END {self._truncate(active_pool.title, self.MAX_TITLE_LENGTH)}\n"
            f"Progress: {progress:.0f}%\n"
            f"\u20a6{active_pool.current_locked_amount:,.0f} of \u20a6{active_pool.target_amount:,.0f}\n"
            f"Deadline: {deadline_str}"
        )

    def _get_total_locked(self, trader) -> float:
        """
        Sums locked contributions across all open pools for this trader.
        In the router, this comes from a DB query — here it's computed
        from trader.pool_contributions if eagerly loaded.
        """
        try:
            return sum(
                c.amount_locked
                for c in trader.pool_contributions
                if c.status == "locked"
            )
        except (AttributeError, TypeError):
            return 0.0

    def _get_active_pool(self, trader):
        """
        Returns the trader's currently active open pool, if any.
        """
        try:
            for contribution in trader.pool_contributions:
                if contribution.status == "locked" and contribution.pool.status == "open":
                    return contribution.pool
        except (AttributeError, TypeError):
            pass
        return None


# Single shared instance
ussd_service = USSDService()
