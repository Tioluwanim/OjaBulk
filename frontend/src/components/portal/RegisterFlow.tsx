"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ArrowLeft, CheckCircle2, Copy, Check } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
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

const initialForm: FormState = {
  name: "",
  phone: "",
  stall_number: "",
  market_name: "",
};

export function RegisterFlow() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTrader, setCreatedTrader] = useState<TraderResponse | null>(null);
  const [copied, setCopied] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): string | null {
    if (form.name.trim().length < 2) return "Enter your full name.";
    if (!normalizeNigerianPhone(form.phone)) {
      return "Enter a valid Nigerian number (e.g. 0801 234 5678).";
    }
    if (form.stall_number.trim().length < 1) return "Enter your stall number.";
    if (form.market_name.trim().length < 2) return "Enter your market name.";
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

    const normalizedPhone = normalizeNigerianPhone(form.phone)!;

    setIsSubmitting(true);
    try {
      const trader = await registerTrader({
        name: form.name.trim(),
        phone: normalizedPhone,
        stall_number: form.stall_number.trim(),
        market_name: form.market_name.trim(),
      });
      setCreatedTrader(trader);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Registration failed. Please try again."
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
    <div className="w-full max-w-md">
      <AnimatePresence mode="wait">
        {!createdTrader ? (
          <motion.form
            key="register-form"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.3 }}
            onSubmit={handleSubmit}
            className="flex flex-col gap-5"
          >
            <a
              href="/portal"
              className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to login
            </a>

            <div>
              <h1 className="font-display text-2xl font-bold text-charcoal">
                Create your account
              </h1>
              <p className="mt-2 text-sm text-charcoal-soft">
                You&apos;ll get a real bank account number instantly &mdash;
                no paperwork, no smartphone required.
              </p>
            </div>

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
                  Create Account
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </motion.form>
        ) : (
          <motion.div
            key="register-success"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col gap-6 text-center"
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success-bg">
              <CheckCircle2 className="h-8 w-8 text-success" />
            </div>

            <div>
              <h1 className="font-display text-2xl font-bold text-charcoal">
                Welcome, {createdTrader.name.split(" ")[0]}!
              </h1>
              <p className="mt-2 text-sm text-charcoal-soft">
                Your virtual account is ready. Send money here anytime &mdash;
                from any bank, USSD, or POS agent.
              </p>
            </div>

            <div className="card-surface flex flex-col gap-3 p-6 text-left">
              <span className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">
                Your OjaBulk Virtual Account
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
                  {copied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
              <div className="flex items-center justify-between border-t border-surface-border pt-3 text-sm">
                <span className="text-charcoal-soft">Bank</span>
                <span className="font-medium text-charcoal">
                  {createdTrader.bank_name}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-charcoal-soft">Account name</span>
                <span className="font-medium text-charcoal">
                  {createdTrader.bank_account_name}
                </span>
              </div>
            </div>

            <a href="/portal" className="btn-gold justify-center">
              Continue to Login
              <ArrowRight className="h-4 w-4" />
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}