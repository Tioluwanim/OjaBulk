"use client";

import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { AnimatedCounter } from "@/components/ui/AnimatedCounter";

const stats = [
  { value: 80, suffix: "%", label: "of Nigeria's workforce is informal" },
  { value: 14, suffix: "M", label: "rely on informal savings alone" },
  { value: 3.33, suffix: "%", label: "lost to collector fees, always", decimals: 2 },
  { value: 320, prefix: "₦", suffix: "B", label: "lost to financial fraud since 2023" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-40 pb-24 md:pt-48 md:pb-32">
      {/* Ambient background texture */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 right-0 h-[500px] w-[500px] rounded-full bg-gold-100/60 blur-3xl" />
        <div className="absolute top-40 -left-40 h-[400px] w-[400px] rounded-full bg-gold-50 blur-3xl" />
      </div>

      <div className="container-oja">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto mb-8 flex w-fit items-center gap-2 rounded-full border border-gold-200 bg-gold-50 px-4 py-2"
        >
          <ShieldCheck className="h-4 w-4 text-gold-600" />
          <span className="text-sm font-medium text-gold-700">
            Built on Nomba Virtual Accounts &mdash; Nomba x DevCareer Hackathon 2026
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="mx-auto max-w-4xl text-center font-display text-display-xl font-bold text-charcoal"
        >
          Pool your money.
          <br />
          Buy at <span className="text-gold-500">wholesale price</span>.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mx-auto mt-6 max-w-2xl text-center text-lg text-charcoal-soft md:text-xl"
        >
          OjaBulk removes the human intermediary from group buying. No one holds
          your pool. No one can disappear with it. Every naira is tracked,
          every refund is automatic.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <Link href="/portal" className="btn-gold">
            Get Your Virtual Account
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a href="#how-it-works" className="btn-outline">
            See How It Works
          </a>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="mx-auto mt-20 grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-4 md:gap-4"
        >
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="card-surface flex flex-col items-center gap-1.5 px-4 py-6 text-center"
            >
              <span className="font-display text-3xl font-bold text-charcoal md:text-4xl">
                <AnimatedCounter
                  value={stat.value}
                  suffix={stat.suffix}
                  prefix={stat.prefix}
                  decimals={stat.decimals ?? 0}
                />
              </span>
              <span className="text-xs leading-snug text-charcoal-soft md:text-sm">
                {stat.label}
              </span>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}