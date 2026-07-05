"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Users, FileWarning, TrendingDown } from "lucide-react";

const painPoints = [
  {
    icon: Users,
    title: "Ajo collapse",
    description:
      "The collector runs away with pooled funds. One person holds everyone's money — and one person can disappear with it.",
    tag: "Trust failure — the root cause",
  },
  {
    icon: FileWarning,
    title: "No record of who paid what",
    description:
      "Contributions are tracked in notebooks or memory. When a dispute arises, there's no way to resolve it.",
    tag: "Audit failure",
  },
  {
    icon: TrendingDown,
    title: "No wholesale access",
    description:
      "Distributors set minimum order quantities far beyond what one trader can afford alone.",
    tag: "Access failure",
  },
  {
    icon: AlertTriangle,
    title: "No guaranteed refund",
    description:
      "When a pooling goal fails, there's no structural mechanism to return anyone's money.",
    tag: "Recovery failure",
  },
];

export function Problem() {
  return (
    <section id="problem" className="bg-cream-dark py-24 md:py-32">
      <div className="container-oja">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="text-sm font-semibold uppercase tracking-wider text-gold-600">
            The Root Problem
          </span>
          <h2 className="mt-4 font-display text-display-md font-bold text-charcoal">
            Traders already know how to pool money.
            <br />
            <span className="text-gold-500">The problem is trust.</span>
          </h2>
          <p className="mt-6 text-lg text-charcoal-soft">
            14 million Nigerians rely on informal savings as their only
            financial channel. SEC Nigeria shut down over 400 fraudulent
            schemes between 2023 and 2026 &mdash; because pooling requires
            trusting a person with money that belongs to many people, and
            people are fallible.
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
          {painPoints.map((point, i) => (
            <motion.div
              key={point.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="card-surface flex flex-col gap-4 p-6"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-danger-bg">
                <point.icon className="h-5 w-5 text-danger" />
              </div>
              <div>
                <h3 className="font-display text-lg font-bold text-charcoal">
                  {point.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-charcoal-soft">
                  {point.description}
                </p>
              </div>
              <span className="mt-auto w-fit rounded-full bg-charcoal/5 px-3 py-1 text-xs font-medium text-charcoal-soft">
                {point.tag}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}