"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ArrowLeft, ShieldCheck } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { requestOtp, verifyOtp } from "@/lib/api/auth";
import { normalizeNigerianPhone, formatPhoneForDisplay } from "@/lib/phone";
import { useAdminAuth } from "@/context/AdminAuthContext";
import { ApiError } from "@/lib/api-client";

type Step = "phone" | "otp";

export function AdminLoginFlow() {
  const { login } = useAdminAuth();
  const [step, setStep] = useState<Step>("phone");
  const [phoneInput, setPhoneInput] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handlePhoneSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const normalized = normalizeNigerianPhone(phoneInput);
    if (!normalized) {
      setError("Enter a valid Nigerian number.");
      return;
    }
    setIsSubmitting(true);
    try {
      await requestOtp(normalized);
      setNormalizedPhone(normalized);
      setStep("otp");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOtpSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (code.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await verifyOtp(normalizedPhone, code);
      login(result);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Invalid code or access denied."
      );
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md">
      <AnimatePresence mode="wait">
        {step === "phone" ? (
          <motion.form
            key="admin-phone"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            onSubmit={handlePhoneSubmit}
            className="flex flex-col gap-5"
          >
            <div>
              <h1 className="font-display text-2xl font-bold text-cream">
                Admin Access
              </h1>
              <p className="mt-2 text-sm text-cream/60">
                Head-of-traders login only. Enter your registered phone
                number.
              </p>
            </div>
            <Input
              type="tel"
              inputMode="tel"
              placeholder="0801 234 5678"
              value={phoneInput}
              onChange={(e) => setPhoneInput(e.target.value)}
              autoFocus
            />
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
              {isSubmitting ? <Spinner className="h-5 w-5" /> : <>Send Code <ArrowRight className="h-4 w-4" /></>}
            </button>
          </motion.form>
        ) : (
          <motion.form
            key="admin-otp"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            onSubmit={handleOtpSubmit}
            className="flex flex-col gap-5"
          >
            <button
              type="button"
              onClick={() => setStep("phone")}
              className="flex w-fit items-center gap-1.5 text-sm font-medium text-cream/60 hover:text-cream"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gold-500/20">
                <ShieldCheck className="h-5 w-5 text-gold-400" />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-cream">Enter code</h1>
                <p className="text-sm text-cream/60">
                  Sent to {formatPhoneForDisplay(normalizedPhone)}
                </p>
              </div>
            </div>
            <Input
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="text-center text-2xl tracking-[0.5em]"
              autoFocus
            />
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
              {isSubmitting ? <Spinner className="h-5 w-5" /> : <>Verify & Enter <ArrowRight className="h-4 w-4" /></>}
            </button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}