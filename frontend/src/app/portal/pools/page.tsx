"use client";

import { useEffect, useState, useCallback } from "react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { JoinPoolCard } from "@/components/portal/JoinPoolCard";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/context/AuthContext";
import { listPools } from "@/lib/api/pools";
import { getMyPools } from "@/lib/api/traders";
import type { PoolResponse } from "@/lib/types";

function PoolsContent() {
  const { trader } = useAuth();
  const [allPools, setAllPools] = useState<PoolResponse[]>([]);
  const [myPoolIds, setMyPoolIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    const [all, mine] = await Promise.all([listPools(), getMyPools()]);
    setAllPools(all.filter((p) => p.status === "open"));
    setMyPoolIds(new Set(mine.map((p) => p.id)));
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  if (!trader || isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8 text-gold-500" />
      </div>
    );
  }

  const marketPools = allPools.filter(
    (p) => p.market_name === trader.market_name
  );

  return (
    <div className="container-oja max-w-2xl py-8 pb-24 md:pb-8">
      <h1 className="font-display text-2xl font-bold text-charcoal">
        Pools in {trader.market_name}
      </h1>
      <p className="mt-1 text-sm text-charcoal-soft">
        Join a pool to start contributing toward wholesale buying power.
      </p>

      <div className="mt-6 flex flex-col gap-4">
        {marketPools.length === 0 ? (
          <div className="card-surface p-8 text-center text-sm text-charcoal-soft">
            No open pools in your market right now. Check back soon.
          </div>
        ) : (
          marketPools.map((pool) => (
            <JoinPoolCard
              key={pool.id}
              pool={pool}
              traderId={trader.id}
              alreadyJoined={myPoolIds.has(pool.id)}
              onJoined={load}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default function TraderPoolsPage() {
  return (
    <RequireAuth>
      <PortalNav />
      <PoolsContent />
    </RequireAuth>
  );
}