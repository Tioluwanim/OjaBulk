"use client";

import { motion } from "framer-motion";
import { Wallet, Lock } from "lucide-react";
import { formatNaira } from "@/lib/format";

interface BalanceCardsProps {
  spendableBalance: number;
  lockedBalance: number;
}

export function BalanceCards({
  spendableBalance,
  lockedBalance,
}: BalanceCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-xl2 bg-gradient-to-br from-gold-500 to-gold-600 p-5 text-cream shadow-gold"
      >
        <div className="flex items-center gap-2 opacity-90">
          <Wallet className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wider">
            Spendable
          </span>
        </div>
        <p className="mt-3 font-display text-2xl font-bold md:text-3xl">
          {formatNaira(spendableBalance)}
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="card-surface p-5"
      >
        <div className="flex items-center gap-2 text-info">
          <Lock className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wider">
            Locked in Pools
          </span>
        </div>
        <p className="mt-3 font-display text-2xl font-bold text-charcoal md:text-3xl">
          {formatNaira(lockedBalance)}
        </p>
      </motion.div>
    </div>
  );
}