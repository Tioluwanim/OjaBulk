import { ArrowDownCircle, ArrowUpCircle, RefreshCcw, Lock } from "lucide-react";
import { formatNaira, formatRelativeTime, ledgerEntryLabel } from "@/lib/format";
import type { LedgerEntryResponse } from "@/lib/types";

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

export function RecentPayments({ entries }: { entries: LedgerEntryResponse[] }) {
  if (entries.length === 0) {
    return (
      <div className="card-surface p-8 text-center text-sm text-charcoal-soft">
        No transactions yet. Send money to your virtual account to get
        started.
      </div>
    );
  }

  return (
    <div className="card-surface divide-y divide-surface-border">
      {entries.slice(0, 3).map((entry) => {
        const Icon = iconMap[entry.entry_type] ?? ArrowDownCircle;
        return (
          <div key={entry.id} className="flex items-center justify-between p-4">
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
          </div>
        );
      })}
    </div>
  );
}