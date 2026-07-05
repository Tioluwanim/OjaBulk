"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, PackageSearch, ScanLine, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdminAuth } from "@/context/AdminAuthContext";

const navItems = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/pools", label: "Pools", icon: PackageSearch },
  { href: "/admin/traders", label: "Traders", icon: Users },
  { href: "/admin/reconciliation", label: "Reconciliation", icon: ScanLine },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { session, logout } = useAdminAuth();

  return (
    <aside className="fixed left-0 top-0 hidden h-screen w-64 flex-col border-r border-surface-border bg-surface p-6 md:flex">
      <Link href="/" className="flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-500 font-display text-lg font-bold text-cream">
          O
        </div>
        <span className="font-display text-xl font-bold text-charcoal">
          Oja<span className="text-gold-500">Bulk</span>
        </span>
      </Link>

      <nav className="mt-10 flex flex-1 flex-col gap-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors",
                active
                  ? "bg-gold-50 text-gold-700"
                  : "text-charcoal-soft hover:bg-cream-dark hover:text-charcoal"
              )}
            >
              <item.icon className="h-4.5 w-4.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-surface-border pt-4">
        <p className="truncate text-sm font-medium text-charcoal">
          {session?.displayName}
        </p>
        <p className="text-xs text-charcoal-soft">{session?.marketName}</p>
        <button
          onClick={logout}
          className="mt-3 flex items-center gap-2 text-sm font-medium text-charcoal-soft hover:text-danger"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}