"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ArrowDownCircle, ArrowUpCircle, RefreshCcw, Lock } from "lucide-react";
import { formatNaira, ledgerEntryLabel } from "@/lib/format";
import type { LedgerEntryResponse } from "@/lib/types";

const iconMap: Record<string, React.ElementType> = {
  spendable_credit: ArrowDownCircle,
  pool_lock: Lock,
  pool_release_payout: ArrowUpCircle,
  pool_refund: RefreshCcw,
};

const colorMap: Record<string, { bg: string; text: string }> = {
  spendable_credit: { bg: "bg-success-bg", text: "text-success" },
  pool_lock: { bg: "bg-info-bg", text: "text-info" },
  pool_release_payout: { bg: "bg-gold-50", text: "text-gold-600" },
  pool_refund: { bg: "bg-cream-dark", text: "text-charcoal-soft" },
};

interface ReceiptSheetProps {
  entry: LedgerEntryResponse | null;
  onClose: () => void;
}

export function ReceiptSheet({ entry, onClose }: ReceiptSheetProps) {
  if (!entry) return null;
  const Icon = iconMap[entry.entry_type] ?? ArrowDownCircle;
  const colors = colorMap[entry.entry_type] ?? colorMap.spendable_credit;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-50 flex items-end justify-center bg-charcoal/40 backdrop-blur-sm md:items-center"
      >
        <motion.div
          initial={{ y: "100%" }}
          animate={{ y: 0 }}
          exit={{ y: "100%" }}
          transition={{ type: "spring", damping: 28, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-md rounded-t-3xl bg-surface p-6 md:rounded-3xl"
        >
          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-cream-dark text-charcoal-soft"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex flex-col items-center text-center">
            <div className={`flex h-14 w-14 items-center justify-center rounded-full ${colors.bg}`}>
              <Icon className={`h-6 w-6 ${colors.text}`} />
            </div>
            <p className="mt-4 text-sm text-charcoal-soft">
              {ledgerEntryLabel(entry.entry_type)}
            </p>
            <p className="mt-1 font-display text-3xl font-bold text-charcoal">
              {formatNaira(entry.amount)}
            </p>
          </div>

          <div className="mt-6 flex flex-col divide-y divide-surface-border rounded-xl2 border border-surface-border">
            <div className="flex items-center justify-between p-4 text-sm">
              <span className="text-charcoal-soft">Balance after</span>
              <span className="font-medium text-charcoal">
                {formatNaira(entry.balance_after)}
              </span>
            </div>
            <div className="flex items-center justify-between p-4 text-sm">
              <span className="text-charcoal-soft">Date</span>
              <span className="font-medium text-charcoal">
                {new Date(entry.created_at).toLocaleString()}
              </span>
            </div>
            {entry.pool_id && (
              <div className="flex items-center justify-between p-4 text-sm">
                <span className="text-charcoal-soft">Pool</span>
                <span className="font-medium text-charcoal">
                  {entry.pool_id.slice(0, 8)}
                </span>
              </div>
            )}
            {entry.note && (
              <div className="p-4 text-sm">
                <span className="text-charcoal-soft">Note</span>
                <p className="mt-1 text-charcoal">{entry.note}</p>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}