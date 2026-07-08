"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { BalanceCards } from "@/components/portal/BalanceCards";
import { VirtualAccountCard } from "@/components/portal/VirtualAccountCard";
import { ActivePoolCard } from "@/components/portal/ActivePoolCard";
import { RecentPayments } from "@/components/portal/RecentPayments";
import { Spinner } from "@/components/ui/Spinner";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/context/AuthContext";
import { getMyLedger, getMyPools, updateMyPayoutDetails } from "@/lib/api/traders";
import { listBanks, lookupAccount } from "@/lib/api/pools";
import { ApiError } from "@/lib/api-client";
import { useBankName } from "@/lib/hooks/useBankName";
import type { TraderLedgerResponse, PoolResponse, BankListItem } from "@/lib/types";
import { Check, Save } from "lucide-react";

interface PayoutFormState {
  payout_bank_code: string;
  payout_account_number: string;
  payout_account_name: string;
}

const emptyPayoutForm: PayoutFormState = {
  payout_bank_code: "",
  payout_account_number: "",
  payout_account_name: "",
};

function HomeContent() {
  const { trader, refreshProfile } = useAuth();
  const [ledger, setLedger] = useState<TraderLedgerResponse | null>(null);
  const [pools, setPools] = useState<PoolResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [payoutForm, setPayoutForm] = useState<PayoutFormState>(emptyPayoutForm);
  const [savingPayout, setSavingPayout] = useState(false);
  const [payoutError, setPayoutError] = useState<string | null>(null);
  const [payoutSuccess, setPayoutSuccess] = useState<string | null>(null);
  const [banks, setBanks] = useState<BankListItem[]>([]);
  const [banksLoading, setBanksLoading] = useState(true);
  const [bankSearch, setBankSearch] = useState("");
  const [bankDropdownOpen, setBankDropdownOpen] = useState(false);
  const [bankLookupLoading, setBankLookupLoading] = useState(false);
  const [bankLookupError, setBankLookupError] = useState<string | null>(null);
  const [resolvedAccountName, setResolvedAccountName] = useState<string | null>(null);
  const bankDropdownRef = useRef<HTMLDivElement>(null);

  const { bankName: payoutBankName } = useBankName(trader?.payout_bank_code);

  const filteredBanks = useMemo(() => {
    if (!bankSearch.trim()) return banks;
    const query = bankSearch.trim().toLowerCase();
    return banks.filter((bank) => bank.name.toLowerCase().includes(query));
  }, [banks, bankSearch]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (trader) {
        setPayoutForm({
          payout_bank_code: trader.payout_bank_code ?? "",
          payout_account_number: trader.payout_account_number ?? "",
          payout_account_name: trader.payout_account_name ?? "",
        });
        setBankSearch(trader.payout_bank_code ? payoutBankName : "");
      }
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [trader, payoutBankName]);

  useEffect(() => {
    async function load() {
      try {
        const [ledgerData, poolsData] = await Promise.all([
          getMyLedger(),
          getMyPools(),
        ]);
        setLedger(ledgerData);
        setPools(poolsData);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    listBanks()
      .then(setBanks)
      .catch(() => {
        setBanks([]);
      })
      .finally(() => setBanksLoading(false));
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (bankDropdownRef.current && !bankDropdownRef.current.contains(e.target as Node)) {
        setBankDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLookupAccount() {
    setBankLookupError(null);
    setResolvedAccountName(null);

    if (!payoutForm.payout_bank_code || !/^\d{10}$/.test(payoutForm.payout_account_number)) {
      return;
    }

    setBankLookupLoading(true);
    try {
      const result = await lookupAccount(
        payoutForm.payout_account_number,
        payoutForm.payout_bank_code,
      );
      setResolvedAccountName(result.account_name);
      setPayoutForm((prev) => ({ ...prev, payout_account_name: result.account_name }));
    } catch (err) {
      setBankLookupError(err instanceof ApiError ? err.message : "Could not verify this account.");
    } finally {
      setBankLookupLoading(false);
    }
  }

  async function handleSavePayoutDetails() {
    setPayoutError(null);
    setPayoutSuccess(null);

    if (!payoutForm.payout_bank_code || !/^\d{10}$/.test(payoutForm.payout_account_number)) {
      setPayoutError("Choose a bank and enter a valid 10-digit account number.");
      return;
    }
    if (!payoutForm.payout_account_name.trim()) {
      setPayoutError("Enter the account name for this payout destination.");
      return;
    }

    setSavingPayout(true);
    try {
      await updateMyPayoutDetails({
        payout_bank_code: payoutForm.payout_bank_code,
        payout_account_number: payoutForm.payout_account_number,
        payout_account_name: payoutForm.payout_account_name,
      });
      await refreshProfile();
      setPayoutSuccess("Payout destination saved. Esusu payouts can now go to this bank account.");
    } catch (err) {
      setPayoutError(err instanceof ApiError ? err.message : "Could not save payout details.");
    } finally {
      setSavingPayout(false);
    }
  }

  function selectBank(bank: BankListItem) {
    setPayoutForm((prev) => ({ ...prev, payout_bank_code: bank.code }));
    setBankSearch(bank.name);
    setBankDropdownOpen(false);
    setResolvedAccountName(null);
    setBankLookupError(null);
    setPayoutSuccess(null);
  }

  if (!trader || isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  const activePool = pools.find((p) => p.status === "open");
  const lockedBalance = activePool?.current_locked_amount ?? 0;

  return (
    <div className="container-oja max-w-2xl py-8 pb-24 md:pb-8">
      <div className="mb-6">
        <p className="text-sm text-charcoal-soft">Welcome back,</p>
        <h1 className="font-display text-2xl font-bold text-charcoal">
          {trader.name.split(" ")[0]}
        </h1>
      </div>

      <div className="flex flex-col gap-6">
        <BalanceCards
          spendableBalance={trader.spendable_balance}
          lockedBalance={lockedBalance}
        />

        <VirtualAccountCard
          accountNumber={trader.virtual_account_number}
          bankName={trader.bank_name}
          accountName={trader.bank_account_name}
        />

        <div className="card-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Esusu payout destination
              </p>
              <h2 className="mt-1 font-display text-lg font-bold text-charcoal">
                Where your future round payouts go
              </h2>
              <p className="mt-1 text-sm text-charcoal-soft">
                Save the bank account you want Esusu/Ajo rounds paid to once it is your turn.
              </p>
            </div>
            <span className="rounded-full bg-gold-50 px-3 py-1 text-xs font-semibold text-gold-700">
              {trader.payout_bank_code ? "Configured" : "Not set"}
            </span>
          </div>

          {trader.payout_bank_code ? (
            <div className="mt-4 rounded-2xl border border-surface-border bg-cream-dark/30 p-4 text-sm text-charcoal">
              <p className="font-medium">{trader.payout_account_name ?? "Account holder"}</p>
              <p className="text-charcoal-soft">
                {trader.payout_account_number} &middot; {payoutBankName || trader.payout_bank_code}
              </p>
            </div>
          ) : (
            <p className="mt-4 rounded-2xl border border-dashed border-surface-border px-4 py-3 text-sm text-charcoal-soft">
              Add one now so Esusu payouts can go straight to a bank account instead of staying in spendable balance.
            </p>
          )}

          <div className="mt-4 grid gap-4">
            <div ref={bankDropdownRef} className="relative">
              <label className="mb-2 block text-sm font-medium text-charcoal">Bank</label>
              <Input
                value={bankSearch}
                disabled={banksLoading}
                onFocus={() => setBankDropdownOpen(true)}
                onChange={(e) => {
                  setBankSearch(e.target.value);
                  setBankDropdownOpen(true);
                }}
                placeholder={banksLoading ? "Loading banks..." : "Search bank name"}
              />
              {bankDropdownOpen && !banksLoading && (
                <div className="absolute z-20 mt-2 max-h-56 w-full overflow-auto rounded-2xl border border-surface-border bg-surface shadow-card">
                  {filteredBanks.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-charcoal-soft">No banks found.</p>
                  ) : (
                    filteredBanks.map((bank) => (
                      <button
                        key={bank.code}
                        type="button"
                        onClick={() => selectBank(bank)}
                        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm hover:bg-cream-dark"
                      >
                        <span className="font-medium text-charcoal">{bank.name}</span>
                        <span className="text-xs text-charcoal-soft">{bank.code}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-charcoal">Account number</label>
                <Input
                  value={payoutForm.payout_account_number}
                  onChange={(e) => {
                    setPayoutForm((prev) => ({
                      ...prev,
                      payout_account_number: e.target.value.replace(/\D/g, "").slice(0, 10),
                    }));
                    setResolvedAccountName(null);
                    setBankLookupError(null);
                  }}
                  onBlur={handleLookupAccount}
                  inputMode="numeric"
                  maxLength={10}
                  placeholder="0123456789"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-charcoal">Account name</label>
                <Input
                  value={payoutForm.payout_account_name}
                  onChange={(e) => setPayoutForm((prev) => ({ ...prev, payout_account_name: e.target.value }))}
                  placeholder="Name on the bank account"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={handleSavePayoutDetails}
                disabled={savingPayout}
                className="btn-gold justify-center disabled:opacity-60"
              >
                {savingPayout ? <Spinner className="h-4 w-4" /> : <><Save className="h-4 w-4" /> Save payout destination</>}
              </button>
              <p className="text-xs text-charcoal-soft">
                This is the bank account Esusu will use when you receive a round payout.
              </p>
            </div>

            {bankLookupLoading && (
              <p className="text-xs text-charcoal-soft">Verifying account name...</p>
            )}
            {resolvedAccountName && (
              <p className="flex items-center gap-1 text-xs text-success">
                <Check className="h-4 w-4" /> Verified: {resolvedAccountName}
              </p>
            )}
            {bankLookupError && (
              <p className="text-xs text-danger">{bankLookupError}</p>
            )}
            {payoutError && (
              <p className="text-xs text-danger">{payoutError}</p>
            )}
            {payoutSuccess && (
              <p className="text-xs text-success">{payoutSuccess}</p>
            )}
          </div>
        </div>

        {activePool && (
          <div>
            <h2 className="mb-3 font-display text-lg font-bold text-charcoal">
              Your Active Pool
            </h2>
            <ActivePoolCard pool={activePool} />
          </div>
        )}

        <div>
          <h2 className="mb-3 font-display text-lg font-bold text-charcoal">
            Recent Activity
          </h2>
          <RecentPayments entries={ledger?.entries ?? []} />
        </div>
      </div>
    </div>
  );
}

export default function TraderHomePage() {
  return (
    <RequireAuth>
      <PortalNav />
      <HomeContent />
    </RequireAuth>
  );
}
