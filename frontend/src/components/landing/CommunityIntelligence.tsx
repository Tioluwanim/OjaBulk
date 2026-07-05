"use client";

import { motion } from "framer-motion";

const features = [
  {
    title: "Real-time group insights",
    description:
      "See every contributor, every payment, and every pool target in an instant dashboard built for market traders.",
  },
  {
    title: "Shared supplier scoring",
    description:
      "Use community feedback to rank wholesalers and reduce risk when sourcing bulk goods.",
  },
  {
    title: "Automatic fairness checks",
    description:
      "OjaBulk flags uneven contributions and reward opportunities so every trader gets the same wholesale value.",
  },
];

export function CommunityIntelligence() {
  return (
    <section id="community" className="bg-[#081E17] py-24 text-white">
      <div className="container-oja">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.32em] text-[#8EE5B8]">
            Community intelligence
          </p>
          <h2 className="mt-4 font-display text-4xl font-bold text-white md:text-5xl">
            The marketplace learns from every pool.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-[#C8F5D0] md:text-lg">
            OjaBulk gives traders visibility into the group, the supply chain, and the fairness of every wholesale purchase.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 26 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: index * 0.14 }}
              className="rounded-[1.75rem] border border-white/10 bg-white/5 p-8 shadow-[0_30px_80px_rgba(0,0,0,0.18)]"
            >
              <div className="mb-4 inline-flex rounded-3xl bg-[#8EE5B8]/15 px-4 py-2 text-sm font-semibold text-[#D8F2D1]">
                {index + 1}
              </div>
              <h3 className="font-display text-2xl font-semibold text-white">
                {feature.title}
              </h3>
              <p className="mt-4 text-base leading-7 text-[#D8F2D1]">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
