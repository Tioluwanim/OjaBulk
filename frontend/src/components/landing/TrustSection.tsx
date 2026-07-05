"use client";

import { motion } from "framer-motion";

const trustPoints = [
  {
    title: "Ledger-first transparency",
    description:
      "Every contribution and every transfer is logged in a single source of truth so traders can always verify the status of their pool.",
  },
  {
    title: "Automated refunds",
    description:
      "Missed targets or order cancellations trigger instant refunds with no manual approval required.",
  },
  {
    title: "Supplier compliance",
    description:
      "We verify supplier credentials and route funds only after successful order confirmation.",
  },
];

export function TrustSection() {
  return (
    <section id="trust" className="bg-[#0B231A] py-24 text-white">
      <div className="container-oja">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.32em] text-[#8EE5B8]">
            Trust built in
          </p>
          <h2 className="mt-4 font-display text-4xl font-bold text-white md:text-5xl">
            Procurement confidence for every group.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-[#C8F5D0] md:text-lg">
            OjaBulk is designed so traders can participate together without fear of lost funds, hidden deals, or broken promises.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {trustPoints.map((point, index) => (
            <motion.div
              key={point.title}
              initial={{ opacity: 0, y: 26 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: index * 0.14 }}
              className="rounded-[1.75rem] border border-white/10 bg-white/5 p-8 shadow-[0_30px_80px_rgba(0,0,0,0.18)]"
            >
              <h3 className="font-display text-2xl font-semibold text-white">
                {point.title}
              </h3>
              <p className="mt-4 text-base leading-7 text-[#D8F2D1]">
                {point.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
