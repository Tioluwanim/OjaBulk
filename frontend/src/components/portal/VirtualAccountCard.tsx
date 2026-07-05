"use client";

import { useState } from "react";
import { Copy, Check, Landmark } from "lucide-react";

interface VirtualAccountCardProps {
  accountNumber: string | null;
  bankName: string | null;
  accountName: string | null;
}

export function VirtualAccountCard({
  accountNumber,
  bankName,
  accountName,
}: VirtualAccountCardProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    if (!accountNumber) return;
    navigator.clipboard.writeText(accountNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!accountNumber) return null;

  return (
    <div className="card-surface flex items-center justify-between p-5">
      <div className="flex items-center gap-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gold-50">
          <Landmark className="h-5 w-5 text-gold-600" />
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
            {bankName} &middot; {accountName}
          </p>
          <p className="font-display text-lg font-bold tracking-wide text-charcoal">
            {accountNumber}
          </p>
        </div>
      </div>
      <button
        onClick={handleCopy}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-gold-50 text-gold-600 transition-colors hover:bg-gold-100"
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  );
}