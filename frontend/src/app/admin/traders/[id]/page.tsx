"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, Landmark, MapPin, Phone } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { LedgerRow } from "@/components/admin/LedgerRow";
import { Spinner } from "@/components/ui/Spinner";
import { getTraderById, getTraderLedgerById } from "@/lib/api/traders";
import { formatNaira } from "@/lib/format";
import type { TraderResponse, TraderLedgerResponse } from "@/lib/types";

function TraderDetailContent({ traderId }: { traderId: string }) {
  const [trader, setTrader] = useState<TraderResponse | null>(null);
  const [ledger, setLedger] = useState<TraderLedgerResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTraderById(traderId), getTraderLedgerById(traderId)])
      .then(([traderData, ledgerData]) => {
        setTrader(traderData);
        setLedger(ledgerData);
      })
      .finally(() => setIsLoading(false));
  }, [traderId]);

  if (isLoading || !trader || !ledger) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <Link
        href="/admin/traders"
        className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to traders
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-charcoal">
            {trader.name}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-charcoal-soft">
            <span className="flex items-center gap-1.5">
              <Phone className="h-4 w-4" /> {trader.phone}
            </span>
            <span className="flex items-center gap-1.5">
              <MapPin className="h-4 w-4" /> Stall {trader.stall_number},{" "}
              {trader.market_name}
            </span>
          </div>
        </div>
      </div>

      {/* Balance cards */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl2 bg-gradient-to-br from-gold-500 to-gold-600 p-5 text-cream shadow-gold">
          <span className="text-xs font-medium uppercase tracking-wider opacity-90">
            Spendable Balance
          </span>
          <p className="mt-2 font-display text-2xl font-bold">
            {formatNaira(trader.spendable_balance)}
          </p>
        </div>

        <div className="card-surface p-5">
          <span className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
            Lifetime Contributed
          </span>
          <p className="mt-2 font-display text-2xl font-bold text-charcoal">
            {formatNaira(trader.total_contributed)}
          </p>
        </div>

        <div className="card-surface p-5">
          <div className="flex items-center gap-2 text-charcoal-soft">
            <Landmark className="h-4 w-4" />
            <span className="text-xs font-medium uppercase tracking-wider">
              Virtual Account
            </span>
          </div>
          <p className="mt-2 font-display text-lg font-bold text-charcoal">
            {trader.virtual_account_number ?? "Not provisioned"}
          </p>
          {trader.bank_name && (
            <p className="text-xs text-charcoal-soft">{trader.bank_name}</p>
          )}
        </div>
      </div>

      {/* Full ledger table */}
      <div className="mt-8">
        <h2 className="mb-3 font-display text-lg font-bold text-charcoal">
          Full Ledger History
        </h2>
        <div className="card-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-cream-dark/50 text-left">
                <th className="p-4 font-medium text-charcoal-soft">Type</th>
                <th className="p-4 font-medium text-charcoal-soft">Note</th>
                <th className="p-4 text-right font-medium text-charcoal-soft">Amount</th>
                <th className="p-4 text-right font-medium text-charcoal-soft">Balance After</th>
                <th className="p-4 text-right font-medium text-charcoal-soft">Date</th>
              </tr>
            </thead>
            <tbody>
              {ledger.entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-charcoal-soft">
                    No ledger entries yet.
                  </td>
                </tr>
              ) : (
                ledger.entries.map((entry) => (
                  <LedgerRow key={entry.id} entry={entry} />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function AdminTraderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <TraderDetailContent traderId={id} />
      </main>
    </RequireAdminAuth>
  );
}