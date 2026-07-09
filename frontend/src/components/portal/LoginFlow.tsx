"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ArrowLeft, ShieldCheck } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { requestOtp, verifyOtp } from "@/lib/api/auth";
import { normalizeNigerianPhone, formatPhoneForDisplay } from "@/lib/phone";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/api-client";

type Step = "phone" | "otp";

export function LoginFlow() {
  const { login } = useAuth();
  const [step, setStep] = useState<Step>("phone");
  const [phoneInput, setPhoneInput] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const cooldownRef = useRef<NodeJS.Timeout | null>(null);

  function startCooldown() {
    setResendCooldown(30);
    cooldownRef.current = setInterval(() => {
      setResendCooldown((prev) => {
        if (prev <= 1) {
          if (cooldownRef.current) clearInterval(cooldownRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  async function handlePhoneSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const normalized = normalizeNigerianPhone(phoneInput);
    if (!normalized) {
      setError(
        "Enter a valid Nigerian number (e.g. 0801 234 5678 or +234 801 234 5678)"
      );
      return;
    }

    setIsSubmitting(true);
    try {
      await requestOtp(normalized);
      setNormalizedPhone(normalized);
      setStep("otp");
      startCooldown();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOtpSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (code.length !== 6) {
      setError("Enter the 6-digit code sent to your phone.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await verifyOtp(normalizedPhone, code);
      await login(result);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Invalid or expired code. Please try again."
      );
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    if (resendCooldown > 0) return;
    setError(null);
    try {
      await requestOtp(normalizedPhone);
      startCooldown();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Couldn't resend the code."
      );
    }
  }

  return (
    <div className="w-full max-w-md">
      <AnimatePresence mode="wait">
        {step === "phone" ? (
          <motion.form
            key="phone-step"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.3 }}
            onSubmit={handlePhoneSubmit}
            className="flex flex-col gap-5"
          >
            <div>
              <h1 className="font-display text-2xl font-bold text-charcoal">
                Log in to OjaBulk
              </h1>
              <p className="mt-2 text-sm text-charcoal-soft">
                Enter your registered phone number. We&apos;ll send a 6-digit
                code by SMS.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-charcoal">
                Phone number
              </label>
              <Input
                type="tel"
                inputMode="tel"
                placeholder="0801 234 5678"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                autoFocus
              />
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
                  Send Code
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <p className="text-center text-xs text-charcoal-soft">
              Not registered yet?{" "}
              <a href="/portal/register" className="font-medium text-gold-600 hover:underline">
                Create your account
              </a>
            </p>
          </motion.form>
        ) : (
          <motion.form
            key="otp-step"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.3 }}
            onSubmit={handleOtpSubmit}
            className="flex flex-col gap-5"
          >
            <button
              type="button"
              onClick={() => {
                setStep("phone");
                setError(null);
                setCode("");
              }}
              className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>

            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gold-50">
                <ShieldCheck className="h-5 w-5 text-gold-600" />
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-charcoal">
                  Enter your code
                </h1>
                <p className="text-sm text-charcoal-soft">
                  Sent to {formatPhoneForDisplay(normalizedPhone)}
                </p>
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-charcoal">
                6-digit code
              </label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="123456"
                value={code}
                onChange={(e) =>
                  setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                className="text-center text-2xl tracking-[0.5em]"
                autoFocus
              />
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
                  Verify & Continue
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleResend}
              disabled={resendCooldown > 0}
              className="text-center text-xs font-medium text-gold-600 hover:underline disabled:cursor-not-allowed disabled:text-charcoal-soft/50 disabled:no-underline"
            >
              {resendCooldown > 0
                ? `Resend code in ${resendCooldown}s`
                : "Resend code"}
            </button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
