"use client";

import { motion } from "framer-motion";
import { ArrowRight, Phone, CheckCircle2 } from "lucide-react";
import Link from "next/link";

const winPoints = [
  "Real-time webhook → balance update, shown live",
  "Underpayment & overpayment handled correctly",
  "Automatic payout AND automatic refund demoed",
  "Reconciliation report: our ledger vs Nomba balance",
  "Live USSD dial on a real phone — no smartphone required",
];

export function DemoCTA() {
  return (
    <section id="demo" className="relative overflow-hidden bg-charcoal py-24 md:py-32">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-20 left-1/4 h-[400px] w-[400px] rounded-full bg-gold-900/40 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-[300px] w-[300px] rounded-full bg-gold-800/30 blur-3xl" />
      </div>

      <div className="container-oja relative">
        <div className="grid grid-cols-1 items-center gap-16 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6 }}
          >
            <span className="text-sm font-semibold uppercase tracking-wider text-gold-400">
              See It In Action
            </span>
            <h2 className="mt-4 font-display text-display-md font-bold text-cream">
              Every naira, tracked in real time.
            </h2>
            <p className="mt-6 text-lg text-cream/70">
              This isn&apos;t a mockup. Send a real test payment and watch the
              full reconciliation pipeline fire &mdash; from webhook
              verification to pool payout to supplier settlement.
            </p>

            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <Link href="/portal" className="btn-gold">
                Open Trader Portal
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/admin"
                className="inline-flex items-center justify-center gap-2 rounded-full border-2 border-cream/20 px-7 py-3.5 font-display font-semibold text-cream transition-all duration-200 hover:border-cream/40 active:scale-[0.98]"
              >
                View Admin Dashboard
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="rounded-xl2 border border-cream/10 bg-cream/5 p-8 backdrop-blur-sm"
          >
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gold-500">
                <Phone className="h-5 w-5 text-cream" />
              </div>
              <span className="font-display font-bold text-cream">
                What judges will see
              </span>
            </div>
            <ul className="flex flex-col gap-4">
              {winPoints.map((point, i) => (
                <motion.li
                  key={point}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.1 }}
                  className="flex items-start gap-3"
                >
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-gold-400" />
                  <span className="text-sm text-cream/80">{point}</span>
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}