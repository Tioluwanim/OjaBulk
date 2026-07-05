import { cn } from "@/lib/utils";
import type { PoolStatus } from "@/lib/types";

const styles: Record<PoolStatus, string> = {
  open: "bg-gold-50 text-gold-700",
  fulfilled: "bg-success-bg text-success",
  refunded: "bg-danger-bg text-danger",
};

const labels: Record<PoolStatus, string> = {
  open: "Open",
  fulfilled: "Fulfilled",
  refunded: "Refunded",
};

export function PoolStatusBadge({ status }: { status: PoolStatus }) {
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 text-xs font-semibold",
        styles[status]
      )}
    >
      {labels[status]}
    </span>
  );
}