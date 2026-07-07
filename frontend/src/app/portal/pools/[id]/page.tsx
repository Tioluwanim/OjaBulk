"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import { ArrowLeft, Store, Calendar, Users, Copy, Check } from "lucide-react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/context/AuthContext";
import { getPool } from "@/lib/api/pools";
import { formatNaira, formatRelativeTime } from "@/lib/format";
import type { PoolDetailResponse } from "@/lib/types";

function statusStyles(status: PoolDetailResponse["status"]) {
  if (status === "fulfilled") return { bg: "bg-success-bg", text: "text-success", ring: "#2F7D5A" };
  if (status === "refunded") return { bg: "bg-danger-bg", text: "text-danger", ring: "#B33A3A" };
  return { bg: "bg-gold-50", text: "text-gold-700", ring: "#C9971F" };
}

function PoolDetailContent({ poolId }: { poolId: string }) {
  const { trader } = useAuth();
  const [pool, setPool] = useState<PoolDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setNotFound(false);
    try {
      const data = await getPool(poolId);
      setPool(data);
    } catch {
      setNotFound(true);
    } finally {
      setIsLoading(false);
    }
  }, [poolId]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  if (notFound || !pool) {
    return (
      <div className="container-oja max-w-2xl py-16 text-center">
        <p className="text-charcoal-soft">
          We couldn&apos;t find that pool. It may have been removed.
        </p>
        <Link href="/portal/pools" className="btn-gold mt-6 inline-flex justify-center">
          Back to pools
        </Link>
      </div>
    );
  }

  const myContribution = trader
    ? pool.contributors.find((c) => c.trader_id === trader.id)
    : undefined;

  const styles = statusStyles(pool.status);

  return (
    <div className="container-oja max-w-2xl py-8 pb-24 md:pb-8">
      <Link
        href="/portal/pools"
        className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pools
      </Link>

      <div className="mt-4 flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-charcoal">{pool.title}</h1>
          <p className="mt-1 text-sm text-charcoal-soft">{pool.market_name}</p>
        </div>
        <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${styles.bg} ${styles.text}`}>
          {pool.status}
        </span>
      </div>

      {pool.status === "fulfilled" && (
        <div className="mt-6 rounded-xl2 bg-success-bg p-5">
          <p className="font-medium text-success">
            This pool reached its target — payment was sent to {pool.supplier_name}
            {pool.fulfilled_at ? ` on ${new Date(pool.fulfilled_at).toLocaleDateString()}` : ""}.
          </p>
        </div>
      )}

      {pool.status === "refunded" && (
        <div className="mt-6 rounded-xl2 bg-danger-bg p-5">
          <p className="font-medium text-danger">
            This pool didn&apos;t reach its target in time. Every contributor&apos;s
            money was returned to their spendable balance.
          </p>
        </div>
      )}

      {myContribution && (
        <div className="mt-6 rounded-xl2 bg-gold-50 p-5">
          <p className="text-xs font-medium uppercase tracking-wider text-gold-700">
            Your contribution
          </p>
          <p className="mt-1 font-display text-xl font-bold text-charcoal">
            {formatNaira(myContribution.amount_locked)}
          </p>
          <p className="mt-0.5 text-xs text-charcoal-soft">
            Status: {myContribution.status}
          </p>
        </div>
      )}

      <div className="mt-6 card-surface p-6">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-charcoal">
            {formatNaira(pool.current_locked_amount)} of {formatNaira(pool.target_amount)}
          </span>
          <span className="text-charcoal-soft">{pool.progress_pct.toFixed(0)}%</span>
        </div>
        <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-cream-dark">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.min(pool.progress_pct, 100)}%`, backgroundColor: styles.ring }}
          />
        </div>
      </div>

      <div className="mt-6 card-surface flex flex-col gap-5 p-6">
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
              {pool.contributors.length} trader{pool.contributors.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
      </div>

      {pool.status === "open" && trader?.virtual_account_number && (
        <div className="mt-6 card-surface p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
            Contribute
          </p>
          <p className="mt-1 text-sm text-charcoal-soft">
            Send money to your OjaBulk virtual account below — it locks toward this
            pool automatically.
          </p>
          <div className="mt-3 flex items-center justify-between rounded-xl bg-cream-dark px-4 py-3">
            <span className="font-display text-lg font-bold text-charcoal">
              {trader.virtual_account_number}
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(trader.virtual_account_number ?? "");
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
              className="flex items-center gap-1 text-sm font-medium text-gold-700"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        <h2 className="mb-3 font-display text-lg font-bold text-charcoal">
          Contributors
        </h2>
        <div className="card-surface overflow-hidden">
          {pool.contributors.length === 0 ? (
            <p className="p-8 text-center text-sm text-charcoal-soft">
              No contributors yet.
            </p>
          ) : (
            <ul className="divide-y divide-surface-border">
              {pool.contributors.map((c) => (
                <li key={c.trader_id} className="flex items-center justify-between p-4 text-sm">
                  <span className="font-medium text-charcoal">
                    {c.trader_id === trader?.id ? "You" : c.trader_id.slice(0, 8)}
                  </span>
                  <span className="text-charcoal-soft">{formatNaira(c.amount_locked)}</span>
                  <span className="text-charcoal-soft">{formatRelativeTime(c.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TraderPoolDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <RequireAuth>
      <PortalNav />
      <PoolDetailContent poolId={id} />
    </RequireAuth>
  );
}
