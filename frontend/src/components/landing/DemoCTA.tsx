"use client";

import { motion } from "framer-motion";
import { ArrowRight, Phone, CheckCircle2, KeyRound, Copy, Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const winPoints = [
  "Real-time webhook → balance update, shown live",
  "Underpayment & overpayment handled correctly",
  "Automatic payout AND automatic refund demoed",
  "Reconciliation report: our ledger vs Nomba balance",
  "Live USSD dial on a real phone — no smartphone required",
];

// Must match DEMO_PHONE_NUMBERS / DEMO_OTP_CODE on the backend and
// scripts/seed_demo_data.py — see services/auth.py's request_otp,
// which checks this list before any SMS/voice delivery is attempted.
// These are fixed so judges can log in without depending on whichever
// SMS provider is or isn't working that day.
const DEMO_TRADER_PHONE = "08099999001";
const DEMO_HEAD_OF_TRADERS_PHONE = "08099999002";
const DEMO_OTP_CODE = "000000";

function CopyableField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="flex w-full items-center justify-between rounded-xl bg-cream/10 px-4 py-2.5 text-left transition-colors hover:bg-cream/15"
    >
      <span>
        <span className="block text-[11px] font-medium uppercase tracking-wider text-cream/50">
          {label}
        </span>
        <span className="font-display text-sm font-semibold text-cream">
          {value}
        </span>
      </span>
      {copied ? (
        <Check className="h-4 w-4 shrink-0 text-gold-400" />
      ) : (
        <Copy className="h-4 w-4 shrink-0 text-cream/40" />
      )}
    </button>
  );
}

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
              <Link
                href="/demo/ussd"
                className="inline-flex items-center justify-center gap-2 rounded-full border-2 border-gold-400/40 px-7 py-3.5 font-display font-semibold text-gold-400 transition-all duration-200 hover:border-gold-400 active:scale-[0.98]"
              >
                Try USSD Demo
              </Link>
            </div>

            <div className="mt-8 rounded-xl2 border border-gold-400/20 bg-gold-400/5 p-6">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-500/20">
                  <KeyRound className="h-4 w-4 text-gold-400" />
                </div>
                <span className="font-display font-bold text-cream">
                  Judge demo login
                </span>
              </div>
              <p className="mb-4 text-sm text-cream/60">
                These accounts use a fixed OTP — no SMS or phone call
                needed. Tap any field to copy.
              </p>
              <div className="flex flex-col gap-2">
                <CopyableField label="Trader portal — phone" value={DEMO_TRADER_PHONE} />
                <CopyableField label="Admin dashboard — phone" value={DEMO_HEAD_OF_TRADERS_PHONE} />
                <CopyableField label="OTP code (both accounts)" value={DEMO_OTP_CODE} />
              </div>
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
