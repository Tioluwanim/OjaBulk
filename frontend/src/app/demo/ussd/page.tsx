import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { UssdSimulator } from "@/components/demo/UssdSimulator";

export default function UssdDemoPage() {
  return (
    <main className="min-h-screen bg-cream-dark py-16">
      <div className="container-oja">
        <Link
          href="/"
          className="flex w-fit items-center gap-1.5 text-sm font-medium text-charcoal-soft hover:text-charcoal"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>

        <div className="mx-auto mt-8 max-w-lg text-center">
          <span className="text-sm font-semibold uppercase tracking-wider text-gold-600">
            Live USSD Demo
          </span>
          <h1 className="mt-3 font-display text-display-md font-bold text-charcoal">
            No smartphone required
          </h1>
          <p className="mt-4 text-charcoal-soft">
            This is a working simulation of the exact USSD session your
            traders use on any phone &mdash; feature phone or smartphone.
            Enter a phone number that&apos;s already registered as a trader
            to see real balance and pool data.
          </p>
        </div>

        <div className="mt-12">
          <UssdSimulator />
        </div>
      </div>
    </main>
  );
}