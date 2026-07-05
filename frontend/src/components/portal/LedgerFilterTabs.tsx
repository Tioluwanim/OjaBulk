"use client";

import { cn } from "@/lib/utils";
import type { LedgerEntryType } from "@/lib/types";

type FilterValue = "all" | LedgerEntryType;

const filters: { value: FilterValue; label: string }[] = [
  { value: "all", label: "All" },
  { value: "spendable_credit", label: "Payments" },
  { value: "pool_lock", label: "Locked" },
  { value: "pool_release_payout", label: "Payouts" },
  { value: "pool_refund", label: "Refunds" },
];

interface LedgerFilterTabsProps {
  active: FilterValue;
  onChange: (value: FilterValue) => void;
}

export function LedgerFilterTabs({ active, onChange }: LedgerFilterTabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {filters.map((f) => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={cn(
            "flex-shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors",
            active === f.value
              ? "bg-gold-500 text-cream"
              : "bg-cream-dark text-charcoal-soft hover:text-charcoal"
          )}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}