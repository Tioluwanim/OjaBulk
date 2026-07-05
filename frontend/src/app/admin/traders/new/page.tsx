"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, CheckCircle2, Copy, Check } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { useAdminAuth } from "@/context/AdminAuthContext";
import { registerTrader } from "@/lib/api/traders";
import { normalizeNigerianPhone } from "@/lib/phone";
import { ApiError } from "@/lib/api-client";
import type { TraderResponse } from "@/lib/types";

interface FormState {
  name: string;
  phone: string;
  stall_number: string;
  market_name: string;
}

function NewTraderContent() {
  const { session } = useAdminAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>({
    name: "",
    phone: "",
    stall_number: "",
    market_name: session?.marketName ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTrader, setCreatedTrader] = useState<TraderResponse | null>(null);
  const [copied, setCopied] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): string | null {
    if (form.name.trim().length < 2) return "Enter the trader's full name.";
    if (!normalizeNigerianPhone(form.phone)) {
      return "Enter a valid Nigerian number (e.g. 0801 234 5678).";
    }
    if (form.stall_number.trim().length < 1) return "Enter a stall number.";
    if (form.market_name.trim().length < 2) return "Enter a market name.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const trader = await registerTrader({
        name: form.name.trim(),
        phone: normalizeNigerianPhone(form.phone)!,
        stall_number: form.stall_number.trim(),
        market_name: form.market_name.trim(),
      });
      setCreatedTrader(trader);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to register trader."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function copyAccountNumber() {
    if (!createdTrader?.virtual_account_number) return;
    navigator.clipboard.writeText(createdTrader.virtual_account_number);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="p-8">
      <Link
        href="/admin/traders"
        className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to traders
      </Link>

      <div className="mx-auto mt-6 max-w-md">
        {!createdTrader ? (
          <>
            <h1 className="font-display text-2xl font-bold text-charcoal">
              Add a Trader
            </h1>
            <p className="mt-1 text-sm text-charcoal-soft">
              Register a trader on their behalf. They&apos;ll be able to log
              in with OTP using the phone number below.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-charcoal">
                  Full name
                </label>
                <Input
                  type="text"
                  placeholder="Adaeze Okafor"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                  autoFocus
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-charcoal">
                  Phone number
                </label>
                <Input
                  type="tel"
                  inputMode="tel"
                  placeholder="0801 234 5678"
                  value={form.phone}
                  onChange={(e) => update("phone", e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-charcoal">
                    Stall number
                  </label>
                  <Input
                    type="text"
                    placeholder="B14"
                    value={form.stall_number}
                    onChange={(e) => update("stall_number", e.target.value)}
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-charcoal">
                    Market
                  </label>
                  <Input
                    type="text"
                    placeholder="Oja Oba"
                    value={form.market_name}
                    onChange={(e) => update("market_name", e.target.value)}
                  />
                </div>
              </div>

              {error && (
                <p className="rounded-xl bg-danger-bg px-4 py-3 text-sm text-danger">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-gold justify-center disabled:opacity-60"
              >
                {isSubmitting ? (
                  <Spinner className="h-5 w-5" />
                ) : (
                  <>
                    Register Trader
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          </>
        ) : (
          <div className="flex flex-col gap-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success-bg">
              <CheckCircle2 className="h-8 w-8 text-success" />
            </div>

            <div>
              <h1 className="font-display text-2xl font-bold text-charcoal">
                {createdTrader.name} is registered
              </h1>
              <p className="mt-2 text-sm text-charcoal-soft">
                Their virtual account is ready. Share this number with them
                so they can start sending money.
              </p>
            </div>

            <div className="card-surface flex flex-col gap-3 p-6 text-left">
              <span className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Virtual Account
              </span>
              <div className="flex items-center justify-between">
                <span className="font-display text-2xl font-bold tracking-wide text-charcoal">
                  {createdTrader.virtual_account_number}
                </span>
                <button
                  type="button"
                  onClick={copyAccountNumber}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-50 text-gold-600 transition-colors hover:bg-gold-100"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
              <div className="flex items-center justify-between border-t border-surface-border pt-3 text-sm">
                <span className="text-charcoal-soft">Phone</span>
                <span className="font-medium text-charcoal">{createdTrader.phone}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setCreatedTrader(null);
                  setForm({
                    name: "",
                    phone: "",
                    stall_number: "",
                    market_name: session?.marketName ?? "",
                  });
                }}
                className="btn-outline flex-1 justify-center"
              >
                Add Another
              </button>
              <button
                onClick={() => router.push(`/admin/traders/${createdTrader.id}`)}
                className="btn-gold flex-1 justify-center"
              >
                View Trader
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NewTraderPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <NewTraderContent />
      </main>
    </RequireAdminAuth>
  );
}