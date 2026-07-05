import Link from "next/link";

export function Footer() {
  return (
    <footer className="bg-cream py-12">
      <div className="container-oja flex flex-col items-center justify-between gap-6 border-t border-surface-border pt-10 md:flex-row">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gold-500 font-display text-sm font-bold text-cream">
            O
          </div>
          <span className="font-display text-lg font-bold text-charcoal">
            Oja<span className="text-gold-500">Bulk</span>
          </span>
        </div>
        <p className="text-sm text-charcoal-soft">
          Built on Nomba Virtual Account Infrastructure &middot; Nomba x
          DevCareer Hackathon 2026
        </p>
        <div className="flex gap-6">
          <Link href="/portal" className="text-sm font-medium text-charcoal-soft hover:text-charcoal">
            Trader Portal
          </Link>
          <Link href="/admin" className="text-sm font-medium text-charcoal-soft hover:text-charcoal">
            Admin
          </Link>
        </div>
      </div>
    </footer>
  );
}