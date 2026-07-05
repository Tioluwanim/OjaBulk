import { ArrowDownCircle, ArrowUpCircle, RefreshCcw, Lock } from "lucide-react";
import { formatNaira, ledgerEntryLabel } from "@/lib/format";
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

export function LedgerRow({ entry }: { entry: LedgerEntryResponse }) {
  const Icon = iconMap[entry.entry_type] ?? ArrowDownCircle;

  return (
    <tr className="border-b border-surface-border last:border-0">
      <td className="p-4">
        <div className="flex items-center gap-3">
          <Icon className={`h-4 w-4 flex-shrink-0 ${colorMap[entry.entry_type]}`} />
          <span className="font-medium text-charcoal">
            {ledgerEntryLabel(entry.entry_type)}
          </span>
        </div>
      </td>
      <td className="p-4 text-charcoal-soft">{entry.note ?? "—"}</td>
      <td className="p-4 text-right font-medium text-charcoal">
        {formatNaira(entry.amount)}
      </td>
      <td className="p-4 text-right text-charcoal-soft">
        {formatNaira(entry.balance_after)}
      </td>
      <td className="p-4 text-right text-charcoal-soft">
        {new Date(entry.created_at).toLocaleString()}
      </td>
    </tr>
  );
}