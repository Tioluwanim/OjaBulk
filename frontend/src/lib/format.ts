export function formatNaira(amount: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-NG", { day: "numeric", month: "short" });
}

export function ledgerEntryLabel(entryType: string): string {
  switch (entryType) {
    case "spendable_credit":
      return "Payment received";
    case "pool_lock":
      return "Locked to pool";
    case "pool_release_payout":
      return "Pool paid out to supplier";
    case "pool_refund":
      return "Refunded to you";
    default:
      return entryType;
  }
}