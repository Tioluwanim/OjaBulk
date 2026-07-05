"use client";

import { motion } from "framer-motion";
import { Wallet, Lock, PackageCheck, ArrowRight } from "lucide-react";

const states = [
  {
    icon: Wallet,
    title: "Spendable Balance",
    description:
      "Money you've sent that isn't locked to any pool. Withdrawable anytime, visible via app or USSD.",
    color: "info",
  },
  {
    icon: Lock,
    title: "Locked Pool Contribution",
    description:
      "Money allocated to a specific pool. Held safely until the pool succeeds or fails — never lost either way.",
    color: "gold",
  },
  {
    icon: PackageCheck,
    title: "Pool Escrow → Payout",
    description:
      "When a pool hits its target, funds move automatically to the supplier. No admin touches the money.",
    color: "success",
  },
];

const colorMap: Record<string, { bg: string; icon: string }> = {
  info: { bg: "bg-info-bg", icon: "text-info" },
  gold: { bg: "bg-gold-50", icon: "text-gold-600" },
  success: { bg: "bg-success-bg", icon: "text-success" },
};

export function Solution() {
  return (
    <section className="bg-cream py-24 md:py-32">
      <div className="container-oja">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="text-sm font-semibold uppercase tracking-wider text-gold-600">
            The OjaBulk Model
          </span>
          <h2 className="mt-4 font-display text-display-md font-bold text-charcoal">
            No human ever holds the pool.
          </h2>
          <p className="mt-6 text-lg text-charcoal-soft">
            Every trader gets a real Nomba virtual account. Every naira that
            arrives is automatically split across three transparent states
            &mdash; and every pool either pays out or refunds, in full,
            without anyone lifting a finger.
          </p>
        </motion.div>

        <div className="relative mt-16">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {states.map((state, i) => (
              <motion.div
                key={state.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="card-surface relative flex flex-col gap-4 p-7"
              >
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-full ${colorMap[state.color].bg}`}
                >
                  <state.icon className={`h-6 w-6 ${colorMap[state.color].icon}`} />
                </div>
                <h3 className="font-display text-xl font-bold text-charcoal">
                  {state.title}
                </h3>
                <p className="text-sm leading-relaxed text-charcoal-soft">
                  {state.description}
                </p>

                {i < states.length - 1 && (
                  <ArrowRight className="absolute -right-8 top-1/2 hidden h-6 w-6 -translate-y-1/2 text-gold-300 md:block" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}