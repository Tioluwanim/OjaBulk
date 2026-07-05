"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, ChevronRight, UserPlus } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { listTraders } from "@/lib/api/traders";
import { formatNaira } from "@/lib/format";
import type { TraderListItem } from "@/lib/types";

function TradersContent() {
  const [traders, setTraders] = useState<TraderListItem[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    listTraders()
      .then(setTraders)
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = traders.filter((t) => {
    const q = query.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      t.phone.includes(q) ||
      t.stall_number.toLowerCase().includes(q) ||
      t.market_name.toLowerCase().includes(q)
    );
  });

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
          <h1 className="font-display text-2xl font-bold text-charcoal">Traders</h1>
          <p className="mt-1 text-sm text-charcoal-soft">
            {traders.length} registered trader{traders.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link 
          href="/admin/traders/new" 
          className="btn-gold inline-flex items-center gap-2 !py-2.5 !px-5 text-sm"
        >
          <UserPlus className="h-4 w-4" />
          Add Trader
        </Link>
      </div>

      <div className="relative mt-6 max-w-md">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-charcoal-soft" />
        <Input
          type="text"
          placeholder="Search by name, phone, stall, or market..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="!py-3 !pl-11 text-sm"
        />
      </div>

      <div className="mt-6 card-surface divide-y divide-surface-border overflow-hidden">
        {filtered.length === 0 ? (
          <p className="p-8 text-center text-sm text-charcoal-soft">
            No traders match your search.
          </p>
        ) : (
          filtered.map((trader) => (
            <Link
              key={trader.id}
              href={`/admin/traders/${trader.id}`}
              className="flex items-center justify-between p-5 transition-colors hover:bg-cream-dark"
            >
              <div>
                <p className="font-display font-bold text-charcoal">
                  {trader.name}
                </p>
                <p className="mt-0.5 text-sm text-charcoal-soft">
                  {trader.phone} &middot; Stall {trader.stall_number} &middot;{" "}
                  {trader.market_name}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="font-display font-bold text-charcoal">
                    {formatNaira(trader.spendable_balance)}
                  </p>
                  <p className="text-xs text-charcoal-soft">spendable</p>
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

export default function AdminTradersPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <TradersContent />
      </main>
    </RequireAdminAuth>
  );
}