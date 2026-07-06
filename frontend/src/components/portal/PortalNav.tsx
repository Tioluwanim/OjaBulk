"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Users, Receipt, LogOut, CircleDollarSign } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { href: "/portal/home", label: "Home", icon: Home },
  { href: "/portal/pools", label: "My Pools", icon: Users },
  { href: "/portal/esusu", label: "Ajo", icon: CircleDollarSign },
  { href: "/portal/history", label: "History", icon: Receipt },
];

export function PortalNav() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <>
      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-surface-border bg-surface/95 backdrop-blur-sm md:hidden">
        <div className="flex items-center justify-around py-2">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-xl px-4 py-2 text-xs font-medium transition-colors",
                  active ? "text-gold-600" : "text-charcoal-soft"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Desktop top bar */}
      <nav className="sticky top-0 z-40 hidden border-b border-surface-border bg-cream/90 backdrop-blur-sm md:block">
        <div className="container-oja flex items-center justify-between py-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gold-500 font-display text-sm font-bold text-cream">
              O
            </div>
            <span className="font-display text-lg font-bold text-charcoal">
              Oja<span className="text-gold-500">Bulk</span>
            </span>
          </Link>

          <div className="flex items-center gap-8">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "text-sm font-medium transition-colors",
                    active ? "text-gold-600" : "text-charcoal-soft hover:text-charcoal"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
            <button
              onClick={logout}
              className="flex items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-danger"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </nav>
    </>
  );
}