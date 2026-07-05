"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useRef } from "react";
import { AnimatedCounter } from "@/components/ui/AnimatedCounter";
import { MagneticButton } from "@/components/ui/MagneticButton";

const stats = [
  { value: 80, suffix: "%", label: "of Nigeria's workforce is informal" },
  { value: 14, suffix: "M", label: "rely on informal savings alone" },
  { value: 3.33, suffix: "%", label: "lost to collector fees, always", decimals: 2 },
  { value: 320, prefix: "₦", suffix: "B", label: "lost to financial fraud since 2023" },
];

const tickerFacts = [
  "40M+ MSMES OPERATING IN NIGERIA",
  "80% OF TRADERS EARN UNDER ₦10,000/DAY",
  "400+ FRAUDULENT SCHEMES SHUT BY SEC",
  "63.5% OF MOBILE MONEY RUNS ON USSD",
  "NO HUMAN EVER HOLDS THE POOL",
];

const headlineWords = ["Pool", "your", "money."];
const headlineWords2 = ["Buy", "at"];

function WordReveal({ words, delayOffset = 0 }: { words: string[]; delayOffset?: number }) {
  return (
    <>
      {words.map((word, i) => (
        <span key={word} className="inline-block overflow-hidden align-bottom">
          <motion.span
            initial={{ y: "110%" }}
            animate={{ y: 0 }}
            transition={{
              duration: 0.8,
              delay: delayOffset + i * 0.08,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="inline-block"
          >
            {word}&nbsp;
          </motion.span>
        </span>
      ))}
    </>
  );
}

export function Hero() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  const blobY1 = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const blobY2 = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const glyphRotate = useTransform(scrollYProgress, [0, 1], [0, 25]);

  return (
    <section
      id="hero"
      ref={heroRef}
      className="relative overflow-hidden pt-40 pb-24 md:pt-48 md:pb-32"
    >
      {/* Parallax ambient background */}
      <motion.div
        style={{ y: blobY1 }}
        className="pointer-events-none absolute -top-40 right-0 h-[500px] w-[500px] rounded-full bg-gold-100/60 blur-3xl"
      />
      <motion.div
        style={{ y: blobY2 }}
        className="pointer-events-none absolute top-40 -left-40 h-[400px] w-[400px] rounded-full bg-gold-50 blur-3xl"
      />

      {/* Floating naira glyphs — decorative, parallax */}
      <motion.span
        style={{ rotate: glyphRotate }}
        className="pointer-events-none absolute left-[8%] top-32 hidden font-display text-6xl font-bold text-gold-200/50 md:block"
      >
        ₦
      </motion.span>
      <motion.span
        style={{ rotate: useTransform(scrollYProgress, [0, 1], [0, -20]) }}
        className="pointer-events-none absolute right-[12%] top-56 hidden font-display text-4xl font-bold text-gold-200/40 md:block"
      >
        ₦
      </motion.span>

      <motion.div style={{ opacity: contentOpacity }} className="container-oja">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto mb-8 flex w-fit items-center gap-2 rounded-full border border-gold-200 bg-gold-50 px-4 py-2"
        >
          <ShieldCheck className="h-4 w-4 text-gold-600" />
          <span className="font-mono text-xs font-medium tracking-wide text-gold-700">
            BUILT ON NOMBA VIRTUAL ACCOUNTS · HACKATHON 2026
          </span>
        </motion.div>

        <h1 className="mx-auto max-w-4xl text-center font-display text-display-xl font-bold text-charcoal">
          <WordReveal words={headlineWords} delayOffset={0.1} />
          <br />
          <WordReveal words={headlineWords2} delayOffset={0.4} />{" "}
          <span className="relative inline-block overflow-hidden align-bottom text-gold-500">
            <motion.span
              initial={{ y: "110%" }}
              animate={{ y: 0 }}
              transition={{ duration: 0.8, delay: 0.56, ease: [0.16, 1, 0.3, 1] }}
              className="inline-block"
            >
              wholesale price.
            </motion.span>
          </span>
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.8 }}
          className="mx-auto mt-6 max-w-2xl text-center text-lg text-charcoal-soft md:text-xl"
        >
          OjaBulk removes the human intermediary from group buying. No one
          holds your pool. No one can disappear with it. Every naira is
          tracked, every refund is automatic.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.95 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <MagneticButton href="/portal" className="btn-gold">
            Get Your Virtual Account
            <ArrowRight className="h-4 w-4" />
          </MagneticButton>
          <MagneticButton href="#how-it-works" className="btn-outline">
            See How It Works
          </MagneticButton>
        </motion.div>

        {/* Stat cards */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 1.1 }}
          className="mx-auto mt-20 grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-4 md:gap-4"
        >
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.6, delay: 1.2 + i * 0.08 }}
              className="card-surface flex flex-col items-center gap-1.5 px-4 py-6 text-center"
            >
              <span className="font-mono text-3xl font-bold text-charcoal md:text-4xl">
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
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Ambient ticker strip */}
      <div className="relative mt-20 overflow-hidden border-y border-surface-border/60 bg-cream-dark/50 py-3">
        <motion.div
          animate={{ x: ["0%", "-50%"] }}
          transition={{ duration: 28, ease: "linear", repeat: Infinity }}
          className="flex w-max gap-12 whitespace-nowrap"
        >
          {[...tickerFacts, ...tickerFacts].map((fact, i) => (
            <span
              key={i}
              className="font-mono text-xs tracking-wider text-charcoal-soft/70"
            >
              {fact}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}