"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Plus } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { PoolStatusBadge } from "@/components/admin/PoolStatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { listPools } from "@/lib/api/pools";
import { formatNaira } from "@/lib/format";
import type { PoolResponse } from "@/lib/types";

function PoolsContent() {
  const [pools, setPools] = useState<PoolResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    listPools()
      .then(setPools)
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-charcoal">Pools</h1>
          <p className="mt-1 text-sm text-charcoal-soft">
            {pools.length} pool{pools.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <Link 
          href="/admin/pools/new" 
          className="btn-gold inline-flex items-center gap-2 !py-2.5 !px-5 text-sm"
        >
          <Plus className="h-4 w-4" />
          New Pool
        </Link>
      </div>

      <div className="mt-6 card-surface divide-y divide-surface-border overflow-hidden">
        {pools.length === 0 ? (
          <p className="p-8 text-center text-sm text-charcoal-soft">
            No pools created yet.
          </p>
        ) : (
          pools.map((pool) => (
            <Link
              key={pool.id}
              href={`/admin/pools/${pool.id}`}
              className="flex items-center justify-between p-5 transition-colors hover:bg-cream-dark"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h3 className="font-display font-bold text-charcoal">
                    {pool.title}
                  </h3>
                  <PoolStatusBadge status={pool.status} />
                </div>
                <p className="mt-1 text-sm text-charcoal-soft">
                  {pool.market_name} &middot; Supplier: {pool.supplier_name}
                </p>
                <div className="mt-3 h-2 w-full max-w-xs overflow-hidden rounded-full bg-cream-dark">
                  <div
                    className="h-full rounded-full bg-gold-500"
                    style={{ width: `${Math.min(pool.progress_pct, 100)}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="font-display font-bold text-charcoal">
                    {formatNaira(pool.current_locked_amount)}
                  </p>
                  <p className="text-xs text-charcoal-soft">
                    of {formatNaira(pool.target_amount)}
                  </p>
                </div>
                <ChevronRight className="h-5 w-5 text-charcoal-soft" />
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

export default function AdminPoolsPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <PoolsContent />
      </main>
    </RequireAdminAuth>
  );
}