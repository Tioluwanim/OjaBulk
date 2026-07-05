"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, RefreshCcw } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Spinner } from "@/components/ui/Spinner";
import { getReconciliation } from "@/lib/api/reports";
import { formatNaira } from "@/lib/format";
import type { ReconciliationResponse } from "@/lib/types";

function ReconciliationContent() {
  const [data, setData] = useState<ReconciliationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function load() {
    setIsLoading(true);
    try {
      const result = await getReconciliation();
      setData(result);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  const hasError = !!data.error;
  const isMatch = data.is_reconciled === true;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-charcoal">
            Reconciliation Report
          </h1>
          <p className="mt-1 text-sm text-charcoal-soft">
            Our ledger total vs. the real Nomba account balance.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 rounded-full border border-surface-border bg-surface px-4 py-2 text-sm font-medium text-charcoal-soft transition-colors hover:text-charcoal"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {hasError ? (
        <div className="mt-8 flex items-center gap-3 rounded-xl2 border border-gold-200 bg-gold-50 p-6">
          <AlertTriangle className="h-6 w-6 flex-shrink-0 text-gold-600" />
          <div>
            <p className="font-medium text-charcoal">
              Couldn&apos;t reach Nomba to fetch the live balance.
            </p>
            <p className="mt-1 text-sm text-charcoal-soft">{data.error}</p>
            <p className="mt-2 text-sm text-charcoal-soft">
              Our internal ledger total is still available below:{" "}
              <span className="font-semibold text-charcoal">
                {formatNaira(data.our_ledger_total)}
              </span>
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* The two big numbers — the differentiator screen */}
          <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="card-surface p-8 text-center">
              <span className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Our Ledger Total
              </span>
              <p className="mt-3 font-display text-4xl font-bold text-charcoal">
                {formatNaira(data.our_ledger_total)}
              </p>
              <p className="mt-2 text-xs text-charcoal-soft">
                Spendable {formatNaira(data.breakdown.spendable_total)} + Locked{" "}
                {formatNaira(data.breakdown.locked_total)}
              </p>
            </div>

            <div className="card-surface p-8 text-center">
              <span className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Nomba Account Balance
              </span>
              <p className="mt-3 font-display text-4xl font-bold text-charcoal">
                {data.nomba_balance !== null ? formatNaira(data.nomba_balance) : "—"}
              </p>
              <p className="mt-2 text-xs text-charcoal-soft">
                {data.currency ?? "NGN"} &middot; checked{" "}
                {data.checked_at ? new Date(data.checked_at).toLocaleTimeString() : "just now"}
              </p>
            </div>
          </div>

          {/* Match / mismatch banner */}
          <div
            className={`mt-6 flex items-center justify-center gap-3 rounded-xl2 p-6 ${
              isMatch ? "bg-success-bg" : "bg-danger-bg"
            }`}
          >
            {isMatch ? (
              <CheckCircle2 className="h-7 w-7 text-success" />
            ) : (
              <XCircle className="h-7 w-7 text-danger" />
            )}
            <div className="text-center">
              <p className={`font-display text-lg font-bold ${isMatch ? "text-success" : "text-danger"}`}>
                {isMatch ? "Fully Reconciled" : "Discrepancy Detected"}
              </p>
              {!isMatch && data.discrepancy !== null && (
                <p className="text-sm text-charcoal-soft">
                  Difference: {formatNaira(Math.abs(data.discrepancy))}
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function ReconciliationPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <ReconciliationContent />
      </main>
    </RequireAdminAuth>
  );
}