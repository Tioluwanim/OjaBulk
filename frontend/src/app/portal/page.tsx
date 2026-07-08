import Link from "next/link";
import { LoginFlow } from "@/components/portal/LoginFlow";
import { ShieldCheck, Lock, Banknote } from "lucide-react";

export default function PortalLoginPage() {
  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Left â€” brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-charcoal p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-20 left-1/4 h-[400px] w-[400px] rounded-full bg-gold-900/40 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-[300px] w-[300px] rounded-full bg-gold-800/30 blur-3xl" />
        </div>

        <Link href="/" className="relative flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-500 font-display text-lg font-bold text-cream">
            O
          </div>
          <span className="font-display text-xl font-bold text-cream">
            Oja<span className="text-gold-400">Bulk</span>
          </span>
        </Link>

        <div className="relative">
          <h2 className="font-display text-display-md font-bold leading-tight text-cream">
            Your money.
            <br />
            Your pool.
            <br />
            No middleman.
          </h2>
          <p className="mt-6 max-w-md text-cream/70">
            OjaBulk gives you a real bank account number. Send money anytime.
            Every naira is tracked &mdash; no one can hold it, hide it, or
            disappear with it.
          </p>

          <div className="mt-10 flex flex-col gap-4">
            <div className="flex items-center gap-3 text-cream/80">
              <ShieldCheck className="h-5 w-5 text-gold-400" />
              <span className="text-sm">HMAC-verified, tamper-proof payments</span>
            </div>
            <div className="flex items-center gap-3 text-cream/80">
              <Lock className="h-5 w-5 text-gold-400" />
              <span className="text-sm">Automatic refunds if a pool doesn&apos;t fill</span>
            </div>
            <div className="flex items-center gap-3 text-cream/80">
              <Banknote className="h-5 w-5 text-gold-400" />
              <span className="text-sm">Real Nomba virtual account, your name</span>
            </div>
          </div>
        </div>

        <p className="relative text-xs text-cream/40">
          Nomba x DevCareer Hackathon 2026
        </p>
      </div>

      {/* Right â€” login form */}
      <div className="flex items-center justify-center bg-cream p-8">
        <LoginFlow />
      </div>
    </main>
  );
}