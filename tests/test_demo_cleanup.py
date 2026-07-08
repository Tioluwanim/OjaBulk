import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MODULES_TO_CLEAR = [
    "core.database",
    "core.config",
    "models",
    "models.trader",
    "models.pool",
    "models.pool_contribution",
    "models.payment",
    "models.ledger_entry",
    "models.identity",
    "models.otp_session",
    "models.esusu",
    "scripts.remove_demo_virtual_account",
]


def bootstrap_database(tmp_path: Path):
    db_path = tmp_path / "ojabulk-test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["NOMBA_WEBHOOK_SECRET"] = "test-secret"
    os.environ["DEMO_PHONE_NUMBERS"] = "08099999001"

    for module_name in MODULES_TO_CLEAR:
        sys.modules.pop(module_name, None)

    core_database = importlib.import_module("core.database")
    importlib.import_module("models")
    importlib.import_module("models.identity")
    importlib.import_module("models.otp_session")
    importlib.import_module("models.esusu")
    core_database.Base.metadata.create_all(bind=core_database.engine)

    return core_database


class DemoCleanupTests(unittest.TestCase):
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
        self.cleanup_script = importlib.import_module("scripts.remove_demo_virtual_account")

    def tearDown(self):
        self.core_database.engine.dispose()
        self.tempdir.cleanup()

    def _session(self):
        return self.core_database.SessionLocal()

    def test_cleanup_deletes_demo_history_but_keeps_real_virtual_account(self):
        session = self._session()
        try:
            trader = self.models_trader.Trader(
                name="Demo Trader",
                phone="08099999001",
                stall_number="A-01",
                market_name="Main Market",
                virtual_account_number="9010000001",
                bank_name="Wema Bank",
                bank_account_name="Demo Trader",
                spendable_balance=250,
                total_contributed=400,
            )
            identity = self.models_identity.Identity(
                phone="08099999001",
                display_name="Demo Trader",
                role=self.models_identity.IdentityRole.TRADER,
                market_name="Main Market",
            )
            session.add_all([trader, identity])
            session.flush()
            identity.linked_trader_id = trader.id

            pool = self.models_pool.Pool(
                title="Demo Pool",
                market_name="Main Market",
                target_amount=1000,
                current_locked_amount=250,
                fulfilled_amount=0,
                minimum_contributors=1,
                supplier_name="Supplier Ltd",
                supplier_account_number="1234567890",
                supplier_bank_code="058",
                status=self.models_pool.PoolStatus.OPEN,
                deadline=datetime(2026, 7, 7, tzinfo=timezone.utc),
            )
            session.add(pool)
            session.flush()

            payment = self.models_payment.Payment(
                trader_id=trader.id,
                amount_received=250,
                nomba_transaction_ref="tx-demo-001",
                spendable_portion=150,
                pool_portion=100,
                pool_id=pool.id,
            )
            session.add(payment)
            session.flush()

            session.add_all(
                [
                    self.models_ledger_entry.LedgerEntry(
                        trader_id=trader.id,
                        pool_id=None,
                        entry_type=self.models_ledger_entry.EntryType.SPENDABLE_CREDIT,
                        amount=150,
                        balance_after=150,
                        note="demo credit",
                    ),
                    self.models_pool_contribution.PoolContribution(
                        trader_id=trader.id,
                        pool_id=pool.id,
                        amount_locked=100,
                        status=self.models_pool_contribution.ContributionStatus.LOCKED,
                    ),
                ]
            )

            cycle = self.models_esusu.EsusuCycle(
                title="Demo Esusu",
                market_name="Main Market",
                contribution_amount=50,
                total_members=1,
                frequency_days=7,
                created_by_identity_id=identity.id,
                status=self.models_esusu.EsusuStatus.OPEN,
            )
            session.add(cycle)
            session.flush()

            member = self.models_esusu.EsusuMember(
                cycle_id=cycle.id,
                trader_id=trader.id,
                payout_position=1,
            )
            session.add(member)
            session.flush()

            round_row = self.models_esusu.EsusuRound(
                cycle_id=cycle.id,
                round_number=1,
                beneficiary_member_id=member.id,
                target_amount=50,
                collected_amount=50,
                status=self.models_esusu.EsusuRoundStatus.OPEN,
            )
            session.add(round_row)
            session.flush()

            session.add(
                self.models_esusu.EsusuContribution(
                    cycle_id=cycle.id,
                    round_id=round_row.id,
                    trader_id=trader.id,
                    payment_id=payment.id,
                    amount=50,
                )
            )

            session.commit()
        finally:
            session.close()

        self.cleanup_script.clear_demo_trader_data()

        session = self._session()
        try:
            refreshed_trader = session.query(self.models_trader.Trader).filter(
                self.models_trader.Trader.phone == "08099999001"
            ).first()

            self.assertIsNotNone(refreshed_trader)
            self.assertEqual(refreshed_trader.virtual_account_number, "9010000001")
            self.assertEqual(refreshed_trader.bank_name, "Wema Bank")
            self.assertEqual(refreshed_trader.bank_account_name, "Demo Trader")
            self.assertEqual(float(refreshed_trader.spendable_balance), 0.0)
            self.assertEqual(float(refreshed_trader.total_contributed), 0.0)

            self.assertEqual(
                session.query(self.models_payment.Payment).count(),
                0,
            )
            self.assertEqual(
                session.query(self.models_ledger_entry.LedgerEntry).count(),
                0,
            )
            self.assertEqual(
                session.query(self.models_pool_contribution.PoolContribution).count(),
                0,
            )
            self.assertEqual(
                session.query(self.models_esusu.EsusuContribution).count(),
                0,
            )
            self.assertEqual(
                session.query(self.models_esusu.EsusuMember).count(),
                0,
            )
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()