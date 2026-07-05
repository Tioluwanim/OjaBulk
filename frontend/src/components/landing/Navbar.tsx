"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-cream/80 backdrop-blur-md border-b border-surface-border py-3"
          : "bg-transparent py-6"
      )}
    >
      <nav className="container-oja flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-500 font-display text-lg font-bold text-cream">
            O
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-charcoal">
            Oja<span className="text-gold-500">Bulk</span>
          </span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          <a href="#problem" className="text-sm font-medium text-charcoal-soft hover:text-charcoal transition-colors">
            The Problem
          </a>
          <a href="#how-it-works" className="text-sm font-medium text-charcoal-soft hover:text-charcoal transition-colors">
            How It Works
          </a>
          <a href="#demo" className="text-sm font-medium text-charcoal-soft hover:text-charcoal transition-colors">
            Live Demo
          </a>
        </div>

        <Link href="/portal" className="btn-gold !py-2.5 !px-5 text-sm">
          Open Trader Portal
        </Link>
      </nav>
    </header>
  );
}