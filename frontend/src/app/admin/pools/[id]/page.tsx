"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, Store, Calendar, Users } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { PoolStatusBadge } from "@/components/admin/PoolStatusBadge";
import { CircularProgress } from "@/components/admin/CircularProgress";
import { Spinner } from "@/components/ui/Spinner";
import { getPool } from "@/lib/api/pools";
import { listTraders } from "@/lib/api/traders";
import { formatNaira, formatRelativeTime } from "@/lib/format";
import type { PoolDetailResponse, TraderListItem } from "@/lib/types";

function PoolDetailContent({ poolId }: { poolId: string }) {
  const [pool, setPool] = useState<PoolDetailResponse | null>(null);
  const [traderMap, setTraderMap] = useState<Record<string, TraderListItem>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPool(poolId), listTraders()])
      .then(([poolData, traders]) => {
        setPool(poolData);
        const map: Record<string, TraderListItem> = {};
        traders.forEach((t) => (map[t.id] = t));
        setTraderMap(map);
      })
      .finally(() => setIsLoading(false));
  }, [poolId]);

  if (isLoading || !pool) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  const isFulfilled = pool.status === "fulfilled";
  const isRefunded = pool.status === "refunded";

  return (
    <div className="p-8">
      <Link
        href="/admin/pools"
        className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pools
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-bold text-charcoal">
              {pool.title}
            </h1>
            <PoolStatusBadge status={pool.status} />
          </div>
          <p className="mt-1 text-sm text-charcoal-soft">{pool.market_name}</p>
        </div>
      </div>

      {(isFulfilled || isRefunded) && (
        <div
          className={`mt-6 rounded-xl2 p-5 ${
            isFulfilled ? "bg-success-bg" : "bg-danger-bg"
          }`}
        >
          <p className={`font-medium ${isFulfilled ? "text-success" : "text-danger"}`}>
            {isFulfilled
              ? `Pool fulfilled — payout sent to ${pool.supplier_name}${
                  pool.fulfilled_at ? ` on ${new Date(pool.fulfilled_at).toLocaleDateString()}` : ""
                }.`
              : "Pool refunded — all contributors received their money back."}
          </p>
          {pool.wholesaler_confirmed_at && (
            <p className="mt-1 text-sm text-charcoal-soft">
              Supplier confirmed order on{" "}
              {new Date(pool.wholesaler_confirmed_at).toLocaleDateString()}.
            </p>
          )}
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Circular progress */}
        <div className="card-surface flex flex-col items-center justify-center p-8">
          <CircularProgress
            percentage={pool.progress_pct}
            color={isFulfilled ? "#2F7D5A" : isRefunded ? "#B33A3A" : "#C9971F"}
          />
          <p className="mt-4 text-center text-sm text-charcoal-soft">
            {formatNaira(pool.current_locked_amount)} of{" "}
            {formatNaira(pool.target_amount)}
          </p>
        </div>

        {/* Pool metadata */}
        <div className="card-surface flex flex-col gap-5 p-6 lg:col-span-2">
          <div className="flex items-start gap-3">
            <Store className="mt-0.5 h-5 w-5 text-gold-600" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Supplier
              </p>
              <p className="font-medium text-charcoal">{pool.supplier_name}</p>
              <p className="text-sm text-charcoal-soft">
                {pool.supplier_account_number} &middot; {pool.supplier_bank_code}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Calendar className="mt-0.5 h-5 w-5 text-gold-600" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Deadline
              </p>
              <p className="font-medium text-charcoal">
                {new Date(pool.deadline).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Users className="mt-0.5 h-5 w-5 text-gold-600" />
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Contributors
              </p>
              <p className="font-medium text-charcoal">
                {pool.contributors.length} trader
                {pool.contributors.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Contributors table */}
      <div className="mt-8">
        <h2 className="mb-3 font-display text-lg font-bold text-charcoal">
          Contributors
        </h2>
        <div className="card-surface overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-cream-dark/50 text-left">
                <th className="p-4 font-medium text-charcoal-soft">Trader</th>
                <th className="p-4 font-medium text-charcoal-soft">Stall</th>
                <th className="p-4 font-medium text-charcoal-soft">Amount Locked</th>
                <th className="p-4 font-medium text-charcoal-soft">Status</th>
                <th className="p-4 font-medium text-charcoal-soft">Joined</th>
              </tr>
            </thead>
            <tbody>
              {pool.contributors.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-charcoal-soft">
                    No contributors yet.
                  </td>
                </tr>
              ) : (
                pool.contributors.map((c) => {
                  const trader = traderMap[c.trader_id];
                  return (
                    <tr key={c.trader_id} className="border-b border-surface-border last:border-0">
                      <td className="p-4 font-medium text-charcoal">
                        {trader?.name ?? c.trader_id.slice(0, 8)}
                      </td>
                      <td className="p-4 text-charcoal-soft">
                        {trader?.stall_number ?? "—"}
                      </td>
                      <td className="p-4 font-medium text-charcoal">
                        {formatNaira(c.amount_locked)}
                      </td>
                      <td className="p-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            c.status === "locked"
                              ? "bg-gold-50 text-gold-700"
                              : c.status === "released"
                              ? "bg-success-bg text-success"
                              : "bg-danger-bg text-danger"
                          }`}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td className="p-4 text-charcoal-soft">
                        {formatRelativeTime(c.created_at)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function AdminPoolDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <PoolDetailContent poolId={id} />
      </main>
    </RequireAdminAuth>
  );
}