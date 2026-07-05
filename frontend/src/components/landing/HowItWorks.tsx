"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { Send, Building2, PiggyBank, Store } from "lucide-react";

const flowSteps = [
  {
    icon: Send,
    title: "Trader sends money",
    description:
      "Any bank USSD, banking app, or POS agent — straight to their unique OjaBulk virtual account number.",
  },
  {
    icon: Building2,
    title: "Nomba verifies & webhooks",
    description:
      "Funds settle instantly. Nomba fires a signed webhook. OjaBulk verifies HMAC and checks idempotency before touching any balance.",
  },
  {
    icon: PiggyBank,
    title: "Auto-allocation",
    description:
      "The reconciliation engine splits the payment between spendable balance and the trader's active pool — down to the naira.",
  },
  {
    icon: Store,
    title: "Payout or refund",
    description:
      "Pool hits target → instant Transfer to the supplier. Deadline passes first → every contributor is refunded automatically.",
  },
];

export function HowItWorks() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 70%", "end 60%"],
  });
  const lineScale = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <section id="how-it-works" className="bg-cream-dark py-24 md:py-32">
      <div className="container-oja">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="font-mono text-xs font-semibold uppercase tracking-widest text-gold-600">
            How It Works
          </span>
          <h2 className="mt-4 font-display text-display-md font-bold text-charcoal">
            From market stall to wholesale supplier
          </h2>
          <p className="mt-6 text-lg text-charcoal-soft">
            Four steps. No admin ever touches the money. Every step produces
            a permanent, uneditable ledger entry.
          </p>
        </motion.div>

        <div ref={containerRef} className="relative mt-20">
          {/* Scroll-drawn connecting line — desktop only */}
          <div className="absolute left-0 right-0 top-8 hidden h-0.5 bg-charcoal/10 lg:block" />
          <motion.div
            style={{ scaleX: lineScale }}
            className="absolute left-0 right-0 top-8 hidden h-0.5 origin-left bg-gold-400 lg:block"
          />

          <div className="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-4">
            {flowSteps.map((step, i) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="relative flex flex-col items-center text-center"
              >
                <div className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full border-4 border-cream-dark bg-gold-500 shadow-gold">
                  <step.icon className="h-7 w-7 text-cream" />
                </div>
                <span className="mt-4 font-mono text-xs font-bold uppercase tracking-wider text-gold-600">
                  Step {i + 1}
                </span>
                <h3 className="mt-2 font-display text-lg font-bold text-charcoal">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-charcoal-soft">
                  {step.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mx-auto mt-16 max-w-2xl rounded-xl2 border border-gold-200 bg-gold-50 p-6 text-center"
        >
          <p className="text-sm leading-relaxed text-charcoal-soft">
            <span className="font-semibold text-charcoal">
              Critical architectural fact:
            </span>{" "}
            Virtual accounts don&apos;t hold balances &mdash; every account
            routes to OjaBulk&apos;s single Nomba parent account. The split
            between spendable, locked, and escrowed is a logical construct we
            build entirely in our ledger.
          </p>
        </motion.div>
      </div>
    </section>
  );
}