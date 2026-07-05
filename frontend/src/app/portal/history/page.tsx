"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { LedgerFilterTabs } from "@/components/portal/LedgerFilterTabs";
import { ReceiptSheet } from "@/components/portal/ReceiptSheet";
import { Spinner } from "@/components/ui/Spinner";
import { getMyLedger } from "@/lib/api/traders";
import { formatNaira, formatRelativeTime, ledgerEntryLabel } from "@/lib/format";
import type { LedgerEntryResponse, LedgerEntryType } from "@/lib/types";
import { ArrowDownCircle, ArrowUpCircle, RefreshCcw, Lock } from "lucide-react";

type FilterValue = "all" | LedgerEntryType;

const iconMap: Record<string, React.ElementType> = {
  spendable_credit: ArrowDownCircle,
  pool_lock: Lock,
  pool_release_payout: ArrowUpCircle,
  pool_refund: RefreshCcw,
};

const colorMap: Record<string, string> = {
  spendable_credit: "text-success",
  pool_lock: "text-info",
  pool_release_payout: "text-gold-600",
  pool_refund: "text-charcoal-soft",
};

function HistoryContent() {
  const [entries, setEntries] = useState<LedgerEntryResponse[]>([]);
  const [filter, setFilter] = useState<FilterValue>("all");
  const [selectedEntry, setSelectedEntry] = useState<LedgerEntryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getMyLedger()
      .then((data) => setEntries(data.entries))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  const filtered =
    filter === "all" ? entries : entries.filter((e) => e.entry_type === filter);

  // Group by date
  const grouped = filtered.reduce<Record<string, LedgerEntryResponse[]>>(
    (acc, entry) => {
      const dateKey = new Date(entry.created_at).toLocaleDateString("en-NG", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
      acc[dateKey] = acc[dateKey] ?? [];
      acc[dateKey].push(entry);
      return acc;
    },
    {}
  );

  return (
    <div className="container-oja max-w-2xl py-8 pb-24 md:pb-8">
      <h1 className="font-display text-2xl font-bold text-charcoal">
        Payment History
      </h1>
      <p className="mt-1 text-sm text-charcoal-soft">
        Every transaction, permanently recorded.
      </p>

      <div className="mt-5">
        <LedgerFilterTabs active={filter} onChange={setFilter} />
      </div>

      <div className="mt-6 flex flex-col gap-6">
        {Object.keys(grouped).length === 0 ? (
          <div className="card-surface p-8 text-center text-sm text-charcoal-soft">
            No transactions match this filter.
          </div>
        ) : (
          Object.entries(grouped).map(([date, dateEntries]) => (
            <div key={date}>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                {date}
              </p>
              <div className="card-surface divide-y divide-surface-border">
                {dateEntries.map((entry) => {
                  const Icon = iconMap[entry.entry_type] ?? ArrowDownCircle;
                  return (
                    <button
                      key={entry.id}
                      onClick={() => setSelectedEntry(entry)}
                      className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-cream-dark"
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`h-5 w-5 ${colorMap[entry.entry_type]}`} />
                        <div>
                          <p className="text-sm font-medium text-charcoal">
                            {ledgerEntryLabel(entry.entry_type)}
                          </p>
                          <p className="text-xs text-charcoal-soft">
                            {formatRelativeTime(entry.created_at)}
                          </p>
                        </div>
                      </div>
                      <span className="font-display text-sm font-bold text-charcoal">
                        {formatNaira(entry.amount)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>

      <ReceiptSheet entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
    </div>
  );
}

export default function HistoryPage() {
  return (
    <RequireAuth>
      <PortalNav />
      <HistoryContent />
    </RequireAuth>
  );
}