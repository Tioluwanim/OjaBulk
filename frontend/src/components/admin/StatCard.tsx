import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  accent?: "gold" | "success" | "info";
}

const accentMap = {
  gold: { bg: "bg-gold-50", icon: "text-gold-600" },
  success: { bg: "bg-success-bg", icon: "text-success" },
  info: { bg: "bg-info-bg", icon: "text-info" },
};

export function StatCard({ icon: Icon, label, value, accent = "gold" }: StatCardProps) {
  return (
    <div className="card-surface p-5">
      <div className={`flex h-10 w-10 items-center justify-center rounded-full ${accentMap[accent].bg}`}>
        <Icon className={`h-5 w-5 ${accentMap[accent].icon}`} />
      </div>
      <p className="mt-4 text-xs font-medium uppercase tracking-wider text-charcoal-soft">
        {label}
      </p>
      <p className="mt-1 font-display text-2xl font-bold text-charcoal">
        {value}
      </p>
    </div>
  );
}