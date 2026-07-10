"""
services/ussd.py

Africa's Talking USSD session handler -- interactive trader menu.

REAL CHANGE from the old read-only version: this used to only support
balance-check and pool-status (no state changes at all, identity was
just "whichever trader owns this phone number"). It now supports:
    1. Registering a new trader account entirely over USSD
       (delegates to services/trader_registration.py -- the exact
       same logic POST /traders uses, so a USSD-registered trader is
       indistinguishable from one registered through the frontend)
    2. Viewing balance AND virtual account number
    3. Joining an open pool (delegates to services/pool_actions.py)
    4. Joining or creating an Esusu/Ajo cycle (delegates to
       services/esusu.py -- the exact same functions routers/esusu.py
       uses)

This is deliberately for TRADER actions only -- registering,
checking balance, joining pools/cycles. It is NOT an admin/head-of-
traders interface: creating a Pool (as opposed to joining one),
confirming a wholesaler order, or managing Esusu payout details all
still require the web frontend and a real Identity/JWT login. USSD
has no login step at all (identity is just "whichever trader owns
this calling phone number"), which is appropriate for read/join
actions a trader takes on their own behalf, but not for actions that
need a verified role like head_of_traders or wholesaler.

USSD response rules:
- CON prefix = session continues (show menu, expect more input)
- END prefix = session terminates (final response)
- Max ~160 chars per response -- kept in mind throughout, though not
  as rigidly enforced as the old read-only version since interactive
  flows inherently need slightly longer prompts/confirmations.
- Session state: Africa's Talking has no server-side session storage
  of its own -- it resends the FULL cumulative input on every request
  (e.g. "3*2" on the third screen of flow 3). This service re-derives
  everything needed each time by re-parsing that full string, rather
  than storing anything server-side keyed by session_id.
"""

import uuid as uuid_module

from sqlalchemy.orm import Session

from models.trader import Trader
from models.pool import Pool, PoolStatus
from models.esusu import EsusuCycle, EsusuStatus

from services.trader_registration import register_trader, TraderRegistrationError
from services.pool_actions import join_pool_for_trader, PoolActionError
from services.esusu import (
    create_cycle,
    join_cycle,
    get_cycle,
    EsusuError,
)
from models.identity import Identity, IdentityRole


class USSDService:

    # Africa's Talking / most carriers cap a single USSD screen around
    # 160-182 chars depending on network. Leaving the raw, unbounded
    # pool.title to interpolate directly (previous behavior) meant a
    # long title could silently truncate the deadline line off the end
    # of the message, or in some carrier implementations return an
    # error instead of a truncated screen. Cap it well under the
    # tightest known limit so the rest of the screen always survives.
    MAX_TITLE_LENGTH = 40

    # How many pools/cycles to list per screen before "more" isn't
    # offered -- keeps a single screen within carrier character limits
    # even with several candidates.
    MAX_LIST_ITEMS = 5

    def _truncate(self, text: str, max_length: int) -> str:
        if text is None:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "\u2026"

    def _normalize_phone(self, phone: str) -> str:
        """
        Africa's Talking sends phone numbers as +234XXXXXXXXXX.
        Trader.phone is stored in whatever format registration used
        (0XXXXXXXXXX is the frontend's convention) -- normalize both
        directions so lookups succeed regardless of which format is
        on file.
        """
        phone = phone.strip().replace(" ", "")
        if phone.startswith("+234"):
            return "0" + phone[4:]
        if phone.startswith("234"):
            return "0" + phone[3:]
        return phone

    def _get_trader_by_phone(self, db: Session, phone_number: str):
        normalized = self._normalize_phone(phone_number)
        alt = "+234" + normalized[1:] if normalized.startswith("0") else normalized
        return db.query(Trader).filter(
            Trader.phone.in_([phone_number, normalized, alt])
        ).first()

    # ==========================================================
    # Entry point
    # ==========================================================

    def handle_session(
        self,
        db: Session,
        session_id: str,
        phone_number: str,
        text: str,
    ) -> str:
        """
        Processes one USSD session step. Africa's Talking resends the
        FULL cumulative input every time (e.g. "3*2*100" on the third
        screen of a flow), so every step re-derives its position from
        scratch by re-splitting `text` on "*" -- there is no
        server-side session state beyond what's in this string.
        """
        trader = self._get_trader_by_phone(db, phone_number)
        steps = text.split("*") if text else []

        # First dial -- show main menu
        if not steps:
            return self._main_menu(trader)

        top = steps[0]

        if top == "1":
            return self._registration_flow(db, phone_number, steps[1:])

        if top == "2":
            if trader is None:
                return self._not_registered()
            return self._account_screen(trader)

        if top == "3":
            if trader is None:
                return self._not_registered()
            return self._join_pool_flow(db, trader, steps[1:])

        if top == "4":
            if trader is None:
                return self._not_registered()
            return self._esusu_flow(db, trader, steps[1:])

        if top == "0":
            return "END Thank you for using OjaBulk."

        return "END Invalid option. Please dial again."

    def _main_menu(self, trader) -> str:
        if trader is None:
            return (
                "CON Welcome to OjaBulk!\n"
                "1. Register\n"
                "0. Exit"
            )
        name = trader.name.split()[0]
        return (
            f"CON Welcome, {name}!\n"
            f"1. Register (n/a)\n"
            f"2. My account\n"
            f"3. Join a pool\n"
            f"4. Esusu/Ajo\n"
            f"0. Exit"
        )

    def _not_registered(self) -> str:
        return (
            "END You are not registered on OjaBulk.\n"
            "Dial again and choose option 1 to register."
        )

    # ==========================================================
    # 1. Registration
    # ==========================================================

    def _registration_flow(self, db: Session, phone_number: str, steps: list[str]) -> str:
        existing = self._get_trader_by_phone(db, phone_number)
        if existing is not None:
            return (
                f"END You're already registered as {existing.name}.\n"
                f"Dial again and choose option 2 for your account."
            )

        if len(steps) == 0:
            return "CON Enter your full name:"

        name = steps[0].strip()
        if not name:
            return "CON Enter your full name:"

        if len(steps) == 1:
            return "CON Enter your market stall number:"

        stall_number = steps[1].strip()
        if not stall_number:
            return "CON Enter your market stall number:"

        if len(steps) == 2:
            return "CON Enter your market name:"

        market_name = steps[2].strip()
        if not market_name:
            return "CON Enter your market name:"

        normalized_phone = self._normalize_phone(phone_number)

        try:
            trader = register_trader(
                db=db,
                name=name,
                phone=normalized_phone,
                stall_number=stall_number,
                market_name=market_name,
            )
        except TraderRegistrationError as e:
            return f"END Registration failed: {self._truncate(str(e), 120)}"

        return (
            f"END Welcome to OjaBulk, {trader.name.split()[0]}!\n"
            f"Your account: {trader.virtual_account_number}\n"
            f"Send money there to start contributing."
        )

    # ==========================================================
    # 2. Account (balance + virtual account number)
    # ==========================================================

    def _account_screen(self, trader) -> str:
        return (
            f"END OjaBulk Account\n"
            f"Spendable: \u20a6{trader.spendable_balance:,.0f}\n"
            f"Locked in pools: \u20a6{self._get_total_locked(trader):,.0f}\n"
            f"Account: {trader.virtual_account_number}"
        )

    def _get_total_locked(self, trader) -> float:
        try:
            return sum(
                c.amount_locked
                for c in trader.pool_contributions
                if c.status == "locked"
            )
        except (AttributeError, TypeError):
            return 0.0

    # ==========================================================
    # 3. Join a pool
    # ==========================================================

    def _get_joinable_pools(self, db: Session, trader) -> list[Pool]:
        query = db.query(Pool).filter(Pool.status == PoolStatus.OPEN)
        if trader.market_name:
            query = query.filter(Pool.market_name == trader.market_name)
        return query.order_by(Pool.created_at.asc()).limit(self.MAX_LIST_ITEMS).all()

    def _join_pool_flow(self, db: Session, trader, steps: list[str]) -> str:
        pools = self._get_joinable_pools(db, trader)

        if len(steps) == 0:
            if not pools:
                return (
                    "END No open pools for your market right now.\n"
                    "Check back later."
                )
            lines = [f"CON Pools in {self._truncate(trader.market_name or '', 20)}:"]
            for i, pool in enumerate(pools, start=1):
                lines.append(f"{i}. {self._truncate(pool.title, 28)}")
            return "\n".join(lines)

        selection = steps[0].strip()
        if not selection.isdigit() or not (1 <= int(selection) <= len(pools)):
            return "END Invalid selection. Please dial again."

        selected_pool = pools[int(selection) - 1]

        try:
            result = join_pool_for_trader(db, selected_pool.id, trader.id)
        except PoolActionError as e:
            return f"END {self._truncate(str(e), 140)}"

        if result["already_joined"]:
            return f"END You're already contributing to {result['pool_title']}."

        return (
            f"END Joined {result['pool_title']}!\n"
            f"Target: \u20a6{result['target']:,.0f}\n"
            f"Send money to your OjaBulk account to contribute."
        )

    # ==========================================================
    # 4. Esusu / Ajo
    # ==========================================================

    def _get_identity_for_trader(self, db: Session, trader) -> Identity | None:
        """
        services/esusu.py's create_cycle/join_cycle take an Identity,
        not a raw Trader -- USSD has no login/JWT step, so this looks
        up the trader's own TRADER-role Identity (created alongside
        them at registration, see services/trader_registration.py) to
        pass through, rather than duplicating create_cycle/join_cycle
        with a trader-only variant.
        """
        return (
            db.query(Identity)
            .filter(
                Identity.linked_trader_id == trader.id,
                Identity.role == IdentityRole.TRADER,
            )
            .order_by(Identity.created_at.desc())
            .first()
        )

    def _get_joinable_cycles(self, db: Session, trader) -> list[EsusuCycle]:
        query = db.query(EsusuCycle).filter(EsusuCycle.status == EsusuStatus.OPEN)
        if trader.market_name:
            query = query.filter(EsusuCycle.market_name == trader.market_name)
        return query.order_by(EsusuCycle.created_at.asc()).limit(self.MAX_LIST_ITEMS).all()

    def _esusu_flow(self, db: Session, trader, steps: list[str]) -> str:
        if len(steps) == 0:
            return (
                "CON Esusu/Ajo\n"
                "1. Join a cycle\n"
                "2. Start a new cycle\n"
                "0. Back"
            )

        sub = steps[0]

        if sub == "1":
            return self._esusu_join_flow(db, trader, steps[1:])

        if sub == "2":
            return self._esusu_create_flow(db, trader, steps[1:])

        return "END Invalid option. Please dial again."

    def _esusu_join_flow(self, db: Session, trader, steps: list[str]) -> str:
        cycles = self._get_joinable_cycles(db, trader)

        if len(steps) == 0:
            if not cycles:
                return (
                    "END No open Esusu cycles for your market right now.\n"
                    "Check back later, or start one yourself."
                )
            lines = [f"CON Esusu cycles in {self._truncate(trader.market_name or '', 15)}:"]
            for i, cycle in enumerate(cycles, start=1):
                lines.append(
                    f"{i}. {self._truncate(cycle.title, 20)} "
                    f"\u20a6{float(cycle.contribution_amount):,.0f}"
                )
            return "\n".join(lines)

        selection = steps[0].strip()
        if not selection.isdigit() or not (1 <= int(selection) <= len(cycles)):
            return "END Invalid selection. Please dial again."

        selected_cycle = cycles[int(selection) - 1]

        identity = self._get_identity_for_trader(db, trader)
        if identity is None:
            return "END Account error: no linked identity found. Contact support."

        try:
            fresh_cycle = get_cycle(db, selected_cycle.id)
            member = join_cycle(db, identity, fresh_cycle)
        except EsusuError as e:
            return f"END {self._truncate(str(e), 140)}"

        return (
            f"END Joined {selected_cycle.title}!\n"
            f"Your position: {member.payout_position}\n"
            f"Contribution: \u20a6{float(selected_cycle.contribution_amount):,.0f} per round"
        )

    def _esusu_create_flow(self, db: Session, trader, steps: list[str]) -> str:
        if len(steps) == 0:
            return "CON Enter a name for this Esusu cycle:"

        title = steps[0].strip()
        if not title:
            return "CON Enter a name for this Esusu cycle:"

        if len(steps) == 1:
            return "CON Enter contribution amount per round (\u20a6):"

        amount_raw = steps[1].strip()
        try:
            contribution_amount = float(amount_raw)
            if contribution_amount <= 0:
                raise ValueError()
        except ValueError:
            return "END Invalid amount. Please dial again and enter numbers only."

        if len(steps) == 2:
            return "CON Enter total number of members:"

        members_raw = steps[2].strip()
        if not members_raw.isdigit() or int(members_raw) < 2:
            return "END Invalid member count. Please dial again (minimum 2)."

        total_members = int(members_raw)

        identity = self._get_identity_for_trader(db, trader)
        if identity is None:
            return "END Account error: no linked identity found. Contact support."

        try:
            cycle = create_cycle(
                db=db,
                identity=identity,
                title=title,
                market_name=trader.market_name,
                contribution_amount=contribution_amount,
                total_members=total_members,
            )
        except EsusuError as e:
            return f"END {self._truncate(str(e), 140)}"

        return (
            f"END Created {cycle.title}!\n"
            f"\u20a6{contribution_amount:,.0f} x {total_members} members\n"
            f"Share with others so they can join."
        )


# Single shared instance
ussd_service = USSDService()
