"use client";

import { useEffect, useState } from "react";
import { Users, PackageSearch, Lock, CheckCircle2 } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { StatCard } from "@/components/admin/StatCard";
import { PoolProgressChart } from "@/components/admin/PoolProgressChart";
import { PoolStatusDonut } from "@/components/admin/PoolStatusDonut";
import { Spinner } from "@/components/ui/Spinner";
import { getStats, getRecentPayments } from "@/lib/api/reports";
import { listPools } from "@/lib/api/pools";
import { formatNaira } from "@/lib/format";
import type { StatsResponse, PoolResponse, RecentPaymentItem } from "@/lib/types";

function DashboardContent() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [pools, setPools] = useState<PoolResponse[]>([]);
  const [recentPayments, setRecentPayments] = useState<RecentPaymentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), listPools(), getRecentPayments()])
      .then(([statsData, poolsData, paymentsData]) => {
        setStats(statsData);
        setPools(poolsData);
        setRecentPayments(paymentsData.items);
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading || !stats) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="font-display text-2xl font-bold text-charcoal">
        Dashboard
      </h1>
      <p className="mt-1 text-sm text-charcoal-soft">
        Live overview across all pools and traders.
      </p>

      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={Users} label="Total Traders" value={stats.total_traders.toString()} accent="info" />
        <StatCard icon={PackageSearch} label="Active Pools" value={stats.active_pools.toString()} accent="gold" />
        <StatCard icon={Lock} label="Total Locked" value={formatNaira(stats.total_locked)} accent="gold" />
        <StatCard icon={CheckCircle2} label="Fulfilled Pools" value={stats.fulfilled_pools.toString()} accent="success" />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card-surface p-6 lg:col-span-2">
          <h2 className="font-display text-lg font-bold text-charcoal">
            Pool Progress
          </h2>
          <p className="text-sm text-charcoal-soft">
            Locked vs. remaining gap — active pools
          </p>
          <div className="mt-4">
            <PoolProgressChart pools={pools} />
          </div>
        </div>

        <div className="card-surface p-6">
          <h2 className="font-display text-lg font-bold text-charcoal">
            Pool Status
          </h2>
          <p className="text-sm text-charcoal-soft">
            Distribution across all pools
          </p>
          <div className="mt-4">
            <PoolStatusDonut pools={pools} />
          </div>
        </div>
      </div>

      <div className="mt-8 card-surface p-6">
        <h2 className="font-display text-lg font-bold text-charcoal">
          Recent Payments
        </h2>
        <p className="text-sm text-charcoal-soft">
          Latest inbound transfers across trader virtual accounts.
        </p>
        <div className="mt-4 divide-y divide-surface-border overflow-hidden rounded-xl2 border border-surface-border">
          {recentPayments.length === 0 ? (
            <p className="p-6 text-sm text-charcoal-soft">
              No payments recorded yet.
            </p>
          ) : (
            recentPayments.map((payment) => (
              <div key={payment.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="text-sm font-medium text-charcoal">{payment.trader_name}</p>
                  <p className="text-xs text-charcoal-soft">
                    {payment.trader_phone}
                    {payment.pool_title ? ` · ${payment.pool_title}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-display text-sm font-bold text-charcoal">
                    {formatNaira(payment.amount_received)}
                  </p>
                  <p className="text-xs text-charcoal-soft">
                    {formatNaira(payment.pool_portion)} locked · {formatNaira(payment.spendable_portion)} spendable
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <DashboardContent />
      </main>
    </RequireAdminAuth>
  );
}