"use client";

import { useEffect, useState } from "react";

interface LedgerLine {
  sectionId: string;
  code: string;
  text: string;
}

const LEDGER_LINES: LedgerLine[] = [
  { sectionId: "hero", code: "000", text: "SESSION STARTED · OJABULK" },
  { sectionId: "problem", code: "001", text: "AJO COLLAPSE DETECTED · TRUST FAILURE" },
  { sectionId: "solution", code: "002", text: "VIRTUAL ACCOUNT ASSIGNED · TRADER" },
  { sectionId: "how-it-works", code: "003", text: "PAYMENT RECEIVED · LOCKED TO POOL" },
  { sectionId: "demo", code: "004", text: "POOL FULFILLED · PAYOUT SENT" },
];

export function LedgerTape() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    LEDGER_LINES.forEach((line, index) => {
      const el = document.getElementById(line.sectionId);
      if (!el) return;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setActiveIndex((prev) => Math.max(prev, index));
          }
        },
        { rootMargin: "-40% 0px -40% 0px" }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => observers.forEach((o) => o.disconnect());
  }, []);

  const visibleLines = LEDGER_LINES.slice(0, activeIndex + 1);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed right-6 top-1/2 z-30 hidden -translate-y-1/2 rotate-1 lg:block"
    >
      <div
        className="w-64 border border-charcoal/10 bg-surface/95 px-5 pb-5 pt-4 shadow-card backdrop-blur-sm"
        style={{
          clipPath:
            "polygon(0% 2%, 4% 0%, 8% 2%, 12% 0%, 16% 2%, 20% 0%, 24% 2%, 28% 0%, 32% 2%, 36% 0%, 40% 2%, 44% 0%, 48% 2%, 52% 0%, 56% 2%, 60% 0%, 64% 2%, 68% 0%, 72% 2%, 76% 0%, 80% 2%, 84% 0%, 88% 2%, 92% 0%, 96% 2%, 100% 0%, 100% 100%, 0% 100%)",
        }}
      >
        <p className="font-mono text-[10px] font-bold tracking-widest text-charcoal-soft">
          OJABULK · LEDGER
        </p>
        <div className="mt-3 flex flex-col gap-2 border-t border-dashed border-charcoal/15 pt-3">
          {visibleLines.map((line, i) => {
            const isLatest = i === visibleLines.length - 1;
            return (
              <div
                key={line.sectionId}
                className="flex items-baseline gap-2 font-mono text-[10px] leading-relaxed transition-opacity duration-500"
                style={{ opacity: isLatest ? 1 : 0.35 }}
              >
                <span className="text-gold-600">{line.code}</span>
                <span className={isLatest ? "text-charcoal" : "text-charcoal-soft"}>
                  {line.text}
                  {isLatest && (
                    <span className="ml-0.5 inline-block h-2.5 w-1 animate-pulse bg-gold-500 align-middle" />
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}