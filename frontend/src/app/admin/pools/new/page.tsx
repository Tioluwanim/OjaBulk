"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { RequireAdminAuth } from "@/components/admin/RequireAdminAuth";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { useAdminAuth } from "@/context/AdminAuthContext";
import { createPool } from "@/lib/api/pools";
import { ApiError } from "@/lib/api-client";

interface FormState {
  title: string;
  target_amount: string;
  supplier_name: string;
  supplier_account_number: string;
  supplier_bank_code: string;
  deadline_date: string;
  deadline_time: string;
}

const initialForm: FormState = {
  title: "",
  target_amount: "",
  supplier_name: "",
  supplier_account_number: "",
  supplier_bank_code: "",
  deadline_date: "",
  deadline_time: "23:59",
};

function NewPoolContent() {
  const { session } = useAdminAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): string | null {
    if (form.title.trim().length < 3) return "Title must be at least 3 characters.";
    const target = parseFloat(form.target_amount);
    if (!target || target <= 0) return "Enter a valid target amount.";
    if (form.supplier_name.trim().length < 2) return "Enter the supplier's name.";
    if (!/^\d{10}$/.test(form.supplier_account_number)) {
      return "Supplier account number must be exactly 10 digits (NUBAN).";
    }
    if (form.supplier_bank_code.trim().length < 1) return "Enter the supplier's bank code.";
    if (!form.deadline_date) return "Choose a deadline date.";
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

    if (!session?.marketName) {
      setError(
        "Your admin account has no market assigned — pools can only be created for your own market."
      );
      return;
    }

    const deadlineIso = new Date(
      `${form.deadline_date}T${form.deadline_time}:00`
    ).toISOString();

    setIsSubmitting(true);
    try {
      const pool = await createPool({
        title: form.title.trim(),
        market_name: session.marketName,
        target_amount: parseFloat(form.target_amount),
        supplier_name: form.supplier_name.trim(),
        supplier_account_number: form.supplier_account_number,
        supplier_bank_code: form.supplier_bank_code.trim(),
        deadline: deadlineIso,
      });
      router.push(`/admin/pools/${pool.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to create pool."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="p-8">
      <Link
        href="/admin/pools"
        className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pools
      </Link>

      <div className="mx-auto mt-6 max-w-xl">
        <h1 className="font-display text-2xl font-bold text-charcoal">
          Create a New Pool
        </h1>
        <p className="mt-1 text-sm text-charcoal-soft">
          This pool will be created for{" "}
          <span className="font-medium text-charcoal">
            {session?.marketName ?? "your market"}
          </span>
          . Traders in your market can join once it&apos;s live.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-charcoal">
              Pool title
            </label>
            <Input
              type="text"
              placeholder="Rice Bulk Buy — July 2026"
              value={form.title}
              onChange={(e) => update("title", e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-charcoal">
              Target amount (₦)
            </label>
            <Input
              type="number"
              min="1"
              step="0.01"
              placeholder="500000"
              value={form.target_amount}
              onChange={(e) => update("target_amount", e.target.value)}
            />
          </div>

          <div className="rounded-xl2 border border-surface-border bg-cream-dark/40 p-5">
            <p className="mb-4 text-sm font-semibold text-charcoal">
              Supplier details
            </p>
            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-charcoal">
                  Supplier name
                </label>
                <Input
                  type="text"
                  placeholder="Kayode Rice Distributors Ltd"
                  value={form.supplier_name}
                  onChange={(e) => update("supplier_name", e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-charcoal">
                    Account number
                  </label>
                  <Input
                    type="text"
                    inputMode="numeric"
                    maxLength={10}
                    placeholder="0123456789"
                    value={form.supplier_account_number}
                    onChange={(e) =>
                      update(
                        "supplier_account_number",
                        e.target.value.replace(/\D/g, "").slice(0, 10)
                      )
                    }
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-charcoal">
                    Bank code
                  </label>
                  <Input
                    type="text"
                    placeholder="058"
                    value={form.supplier_bank_code}
                    onChange={(e) => update("supplier_bank_code", e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-charcoal">
              Deadline
            </label>
            <div className="grid grid-cols-2 gap-4">
              <Input
                type="date"
                value={form.deadline_date}
                onChange={(e) => update("deadline_date", e.target.value)}
              />
              <Input
                type="time"
                value={form.deadline_time}
                onChange={(e) => update("deadline_time", e.target.value)}
              />
            </div>
            <p className="mt-2 text-xs text-charcoal-soft">
              If the target isn&apos;t reached by this time, all contributors
              are automatically refunded.
            </p>
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
                Create Pool
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function NewPoolPage() {
  return (
    <RequireAdminAuth>
      <AdminSidebar />
      <main className="md:ml-64">
        <NewPoolContent />
      </main>
    </RequireAdminAuth>
  );
}