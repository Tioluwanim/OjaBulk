"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { formatNaira } from "@/lib/format";
import { joinPool } from "@/lib/api/pools";
import { ApiError } from "@/lib/api-client";
import type { PoolResponse } from "@/lib/types";

interface JoinPoolCardProps {
  pool: PoolResponse;
  traderId: string;
  alreadyJoined: boolean;
  onJoined: () => void;
}

export function JoinPoolCard({
  pool,
  traderId,
  alreadyJoined,
  onJoined,
}: JoinPoolCardProps) {
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justJoined, setJustJoined] = useState(false);

  async function handleJoin() {
    setError(null);
    setIsJoining(true);
    try {
      await joinPool(pool.id, traderId);
      setJustJoined(true);
      onJoined();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't join pool.");
    } finally {
      setIsJoining(false);
    }
  }

  const joined = alreadyJoined || justJoined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-surface p-5"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-lg font-bold text-charcoal">
            {pool.title}
          </h3>
          <p className="mt-0.5 text-sm text-charcoal-soft">
            Supplier: {pool.supplier_name}
          </p>
        </div>
        {joined && (
          <span className="flex items-center gap-1 rounded-full bg-success-bg px-3 py-1 text-xs font-semibold text-success">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Joined
          </span>
        )}
      </div>

      <div className="mt-4">
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-cream-dark">
          <div
            className="h-full rounded-full bg-gold-500 transition-all duration-500"
            style={{ width: `${Math.min(pool.progress_pct, 100)}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className="font-medium text-charcoal">
            {formatNaira(pool.current_locked_amount)} of{" "}
            {formatNaira(pool.target_amount)}
          </span>
          <span className="text-charcoal-soft">
            Deadline {new Date(pool.deadline).toLocaleDateString()}
          </span>
        </div>
      </div>

      {error && (
        <p className="mt-3 rounded-xl bg-danger-bg px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}

      {!joined && (
        <button
          onClick={handleJoin}
          disabled={isJoining}
          className="btn-gold mt-4 w-full justify-center !py-2.5 text-sm disabled:opacity-60"
        >
          {isJoining ? "Joining..." : "Join This Pool"}
        </button>
      )}

      {joined && (
        <p className="mt-4 text-xs text-charcoal-soft">
          Send money to your virtual account and it will automatically lock
          toward this pool.
        </p>
      )}
    </motion.div>
  );
}