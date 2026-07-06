import asyncio
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch


MODULES_TO_CLEAR = [
    "core.database",
    "models",
    "models.trader",
    "models.pool",
    "models.pool_contribution",
    "models.payment",
    "models.ledger_entry",
    "models.identity",
    "models.otp_session",
    "models.esusu",
    "routers.reports",
    "routers.webhooks",
    "routers.esusu",
    "engine.reconciliation",
    "engine.payout",
    "engine.refund",
    "services.esusu",
    "services.reports",
    "services.webhooks",
    "services.sms",
    "services.transfers",
]


def bootstrap_database(tmp_path: Path):
    db_path = tmp_path / "ojabulk-test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["NOMBA_WEBHOOK_SECRET"] = "test-secret"

    for module_name in MODULES_TO_CLEAR:
        sys.modules.pop(module_name, None)

    core_database = importlib.import_module("core.database")
    importlib.import_module("models")
    importlib.import_module("models.identity")
    importlib.import_module("models.otp_session")
    importlib.import_module("models.esusu")
    core_database.Base.metadata.create_all(bind=core_database.engine)

    return core_database


class CoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tempdir.name)
        self.core_database = bootstrap_database(self.tmp_path)

        self.models_trader = importlib.import_module("models.trader")
        self.models_pool = importlib.import_module("models.pool")
        self.models_pool_contribution = importlib.import_module("models.pool_contribution")
        self.models_payment = importlib.import_module("models.payment")
        self.models_ledger_entry = importlib.import_module("models.ledger_entry")
        self.models_identity = importlib.import_module("models.identity")
        self.models_esusu = importlib.import_module("models.esusu")
        self.reports_router = importlib.import_module("routers.reports")
        self.webhooks_router = importlib.import_module("routers.webhooks")
        self.esusu_service = importlib.import_module("services.esusu")
        self.payout_engine = importlib.import_module("engine.payout")
        self.refund_engine = importlib.import_module("engine.refund")

    def tearDown(self):
        self.core_database.engine.dispose()
        self.tempdir.cleanup()

    def _session(self):
        return self.core_database.SessionLocal()

    def test_reconciliation_report_is_ledger_driven(self):
        session = self._session()
        try:
            trader = self.models_trader.Trader(
                name="Ada Trader",
                phone="08012345678",
                stall_number="B-01",
                market_name="Main Market",
                spendable_balance=0,
                total_contributed=0,
            )
            pool = self.models_pool.Pool(
                title="Rice Bulk Buy",
                market_name="Main Market",
                target_amount=1000,
                current_locked_amount=0,
                fulfilled_amount=0,
                minimum_contributors=1,
                supplier_name="Supplier Ltd",
                supplier_account_number="1234567890",
                supplier_bank_code="058",
                status=self.models_pool.PoolStatus.OPEN,
                deadline=datetime(2026, 7, 7, tzinfo=timezone.utc),
            )
            session.add_all([trader, pool])
            session.flush()

            session.add_all(
                [
                    self.models_ledger_entry.LedgerEntry(
                        trader_id=trader.id,
                        pool_id=None,
                        entry_type=self.models_ledger_entry.EntryType.SPENDABLE_CREDIT,
                        amount=1000,
                        balance_after=1000,
                        note="credit",
                    ),
                    self.models_ledger_entry.LedgerEntry(
                        trader_id=trader.id,
                        pool_id=pool.id,
                        entry_type=self.models_ledger_entry.EntryType.POOL_LOCK,
                        amount=700,
                        balance_after=300,
                        note="lock",
                    ),
                    self.models_ledger_entry.LedgerEntry(
                        trader_id=trader.id,
                        pool_id=pool.id,
                        entry_type=self.models_ledger_entry.EntryType.POOL_RELEASE_PAYOUT,
                        amount=200,
                        balance_after=300,
                        note="release",
                    ),
                    self.models_ledger_entry.LedgerEntry(
                        trader_id=trader.id,
                        pool_id=pool.id,
                        entry_type=self.models_ledger_entry.EntryType.POOL_REFUND,
                        amount=50,
                        balance_after=1050,
                        note="refund",
                    ),
                ]
            )
            session.commit()

            with patch.object(self.reports_router.reports_service, "reconcile", return_value={
                "nomba_balance": 1550.0,
                "our_ledger_total": 1550.0,
                "discrepancy": 0.0,
                "is_reconciled": True,
                "currency": "NGN",
                "checked_at": "2026-07-06T00:00:00Z",
            }):
                result = self.reports_router.get_reconciliation_report(db=session)

            self.assertEqual(result.breakdown.spendable_total, 1050.0)
            self.assertEqual(result.breakdown.locked_total, 500.0)
            self.assertEqual(result.our_ledger_total, 1550.0)
            self.assertTrue(result.is_reconciled)
        finally:
            session.close()

    def test_webhook_duplicate_transaction_short_circuits_reconciliation(self):
        session = self._session()
        try:
            trader = self.models_trader.Trader(
                name="Ada Trader",
                phone="08012345678",
                stall_number="B-01",
                market_name="Main Market",
                virtual_account_number="9010000001",
                bank_name="Wema Bank",
                bank_account_name="Ada Trader",
                spendable_balance=0,
                total_contributed=0,
            )
            session.add(trader)
            session.flush()
            session.add(
                self.models_payment.Payment(
                    trader_id=trader.id,
                    amount_received=500,
                    nomba_transaction_ref="tx-123",
                    spendable_portion=500,
                    pool_portion=0,
                    pool_id=None,
                )
            )
            session.commit()

            class FakeRequest:
                def __init__(self, body: bytes):
                    self._body = body
                    self.headers = {"x-nomba-signature": "any-signature"}

                async def body(self):
                    return self._body

            class FakeBackgroundTasks:
                def __init__(self):
                    self.tasks = []

                def add_task(self, func, *args, **kwargs):
                    self.tasks.append((func, args, kwargs))

            payload = {
                "requestId": "tx-123",
                "event_type": "payment_success",
                "data": {
                    "transaction": {
                        "aliasAccountNumber": "9010000001",
                        "transactionAmount": 500,
                    },
                    "customer": {},
                },
            }

            with patch.object(self.webhooks_router.webhook_service, "verify", return_value=None), patch.object(
                self.webhooks_router.webhook_service,
                "parse_payload",
                return_value={
                    "transaction_ref": "tx-123",
                    "virtual_account_number": "9010000001",
                    "amount": 500.0,
                },
            ):
                self.webhooks_router.SessionLocal = self.core_database.SessionLocal
                result = asyncio.run(
                    self.webhooks_router.receive_nomba_webhook(
                        FakeRequest(json.dumps(payload).encode("utf-8")),
                        FakeBackgroundTasks(),
                    )
                )

            self.assertEqual(result["note"], "duplicate transaction ignored")
        finally:
            session.close()

    def test_payout_persists_transfer_and_fulfilled_state(self):
        session = self._session()
        try:
            trader = self.models_trader.Trader(
                name="Ada Trader",
                phone="08012345678",
                stall_number="B-01",
                market_name="Main Market",
                spendable_balance=0,
                total_contributed=0,
            )
            pool = self.models_pool.Pool(
                title="Rice Bulk Buy",
                market_name="Main Market",
                target_amount=1000,
                current_locked_amount=1000,
                fulfilled_amount=0,
                minimum_contributors=1,
                supplier_name="Supplier Ltd",
                supplier_account_number="1234567890",
                supplier_bank_code="058",
                status=self.models_pool.PoolStatus.OPEN,
                deadline=datetime(2026, 7, 7, tzinfo=timezone.utc),
            )
            session.add_all([trader, pool])
            session.flush()
            contribution = self.models_pool_contribution.PoolContribution(
                trader_id=trader.id,
                pool_id=pool.id,
                amount_locked=1000,
                status=self.models_pool_contribution.ContributionStatus.LOCKED,
            )
            session.add(contribution)
            session.commit()

            with patch.object(self.payout_engine.transfer_service, "send_to_supplier", return_value={"transfer_ref": "transfer-123"}), patch.object(
                self.payout_engine.sms_service,
                "send_pool_fulfilled",
                return_value=True,
            ):
                result = self.payout_engine.trigger_payout(db=session, pool=pool)

            session.refresh(pool)
            session.refresh(contribution)

            self.assertEqual(result["transfer_ref"], "transfer-123")
            self.assertEqual(pool.status, self.models_pool.PoolStatus.FULFILLED)
            self.assertIsNotNone(pool.fulfilled_at)
            self.assertEqual(float(pool.fulfilled_amount), 1000.0)
            self.assertEqual(pool.nomba_transfer_ref, "transfer-123")
            self.assertEqual(contribution.status, self.models_pool_contribution.ContributionStatus.RELEASED)
        finally:
            session.close()

    def test_refund_marks_refunded_at_and_returns_funds(self):
        session = self._session()
        try:
            trader = self.models_trader.Trader(
                name="Ada Trader",
                phone="08012345678",
                stall_number="B-01",
                market_name="Main Market",
                spendable_balance=0,
                total_contributed=0,
            )
            pool = self.models_pool.Pool(
                title="Beans Bulk Buy",
                market_name="Main Market",
                target_amount=1000,
                current_locked_amount=100,
                fulfilled_amount=0,
                minimum_contributors=1,
                supplier_name="Supplier Ltd",
                supplier_account_number="1234567890",
                supplier_bank_code="058",
                status=self.models_pool.PoolStatus.OPEN,
                deadline=datetime(2026, 7, 5, tzinfo=timezone.utc),
            )
            session.add_all([trader, pool])
            session.flush()
            contribution = self.models_pool_contribution.PoolContribution(
                trader_id=trader.id,
                pool_id=pool.id,
                amount_locked=100,
                status=self.models_pool_contribution.ContributionStatus.LOCKED,
            )
            session.add(contribution)
            session.commit()

            with patch.object(self.refund_engine.sms_service, "send_pool_refunded", return_value=True):
                result = self.refund_engine.refund_pool(db=session, pool=pool)

            session.refresh(pool)
            session.refresh(trader)
            session.refresh(contribution)

            self.assertEqual(result["total_refunded"], 100.0)
            self.assertEqual(pool.status, self.models_pool.PoolStatus.REFUNDED)
            self.assertIsNotNone(pool.refunded_at)
            self.assertEqual(float(trader.spendable_balance), 100.0)
            self.assertEqual(contribution.status, self.models_pool_contribution.ContributionStatus.REFUNDED)
        finally:
            session.close()

    def test_esusu_cycle_advances_through_rounds(self):
        session = self._session()
        try:
            trader_a = self.models_trader.Trader(
                name="Ada Trader",
                phone="08012345678",
                stall_number="B-01",
                market_name="Main Market",
                spendable_balance=0,
                total_contributed=0,
            )
            trader_b = self.models_trader.Trader(
                name="Bola Trader",
                phone="08012345679",
                stall_number="B-02",
                market_name="Main Market",
                spendable_balance=0,
                total_contributed=0,
            )
            session.add_all([trader_a, trader_b])
            session.flush()

            identity_a = self.models_identity.Identity(
                phone=trader_a.phone,
                display_name=trader_a.name,
                role=self.models_identity.IdentityRole.TRADER,
                market_name=trader_a.market_name,
                linked_trader_id=trader_a.id,
            )
            identity_b = self.models_identity.Identity(
                phone=trader_b.phone,
                display_name=trader_b.name,
                role=self.models_identity.IdentityRole.TRADER,
                market_name=trader_b.market_name,
                linked_trader_id=trader_b.id,
            )
            session.add_all([identity_a, identity_b])
            session.commit()

            identity_a = session.query(self.models_identity.Identity).filter_by(phone=trader_a.phone).first()
            identity_b = session.query(self.models_identity.Identity).filter_by(phone=trader_b.phone).first()

            cycle = self.esusu_service.create_cycle(
                db=session,
                identity=identity_a,
                title="Market Savings Circle",
                market_name="Main Market",
                contribution_amount=100,
                total_members=2,
                frequency_days=7,
                description="Rotating savings for market traders",
            )

            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.esusu_service.join_cycle(session, identity_a, cycle)
            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.esusu_service.join_cycle(session, identity_b, cycle)

            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.assertEqual(cycle.status, self.models_esusu.EsusuStatus.ACTIVE)
            self.assertEqual(cycle.current_round_number, 1)

            result_1 = self.esusu_service.record_contribution(session, identity_a, cycle)
            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.assertFalse(result_1["round_paid"])
            self.assertEqual(cycle.current_round_number, 1)

            result_2 = self.esusu_service.record_contribution(session, identity_b, cycle)
            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.assertTrue(result_2["round_paid"])
            self.assertEqual(cycle.current_round_number, 2)
            self.assertEqual(cycle.status, self.models_esusu.EsusuStatus.ACTIVE)

            result_3 = self.esusu_service.record_contribution(session, identity_a, cycle)
            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.assertFalse(result_3["round_paid"])
            self.assertEqual(cycle.current_round_number, 2)

            result_4 = self.esusu_service.record_contribution(session, identity_b, cycle)
            cycle = self.esusu_service.get_cycle(session, cycle.id)
            self.assertTrue(result_4["round_paid"])
            self.assertTrue(result_4["cycle_completed"])
            self.assertEqual(cycle.status, self.models_esusu.EsusuStatus.COMPLETED)
            self.assertIsNotNone(cycle.completed_at)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()