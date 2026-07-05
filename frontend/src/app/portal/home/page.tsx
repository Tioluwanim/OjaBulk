"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { BalanceCards } from "@/components/portal/BalanceCards";
import { VirtualAccountCard } from "@/components/portal/VirtualAccountCard";
import { ActivePoolCard } from "@/components/portal/ActivePoolCard";
import { RecentPayments } from "@/components/portal/RecentPayments";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/context/AuthContext";
import { getMyLedger, getMyPools } from "@/lib/api/traders";
import type { TraderLedgerResponse, PoolResponse } from "@/lib/types";

function HomeContent() {
  const { trader } = useAuth();
  const [ledger, setLedger] = useState<TraderLedgerResponse | null>(null);
  const [pools, setPools] = useState<PoolResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

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
          {trader.name.split(" ")[0]} 👋
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