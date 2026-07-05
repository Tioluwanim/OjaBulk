import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { formatNaira } from "@/lib/format";
import type { PoolResponse } from "@/lib/types";

export function ActivePoolCard({ pool }: { pool: PoolResponse }) {
  return (
    <Link
      href={`/portal/pools/${pool.id}`}
      className="card-surface block p-5 transition-shadow hover:shadow-card-hover"
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-medium uppercase tracking-wider text-gold-600">
            Active Pool
          </span>
          <h3 className="mt-1 font-display text-lg font-bold text-charcoal">
            {pool.title}
          </h3>
        </div>
        <ArrowRight className="h-5 w-5 text-charcoal-soft" />
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
            {pool.progress_pct.toFixed(0)}%
          </span>
        </div>
      </div>
    </Link>
  );
}