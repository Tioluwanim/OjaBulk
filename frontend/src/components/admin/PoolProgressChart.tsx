"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { PoolResponse } from "@/lib/types";
import { formatNaira } from "@/lib/format";

interface PoolProgressChartProps {
  pools: PoolResponse[];
}

export function PoolProgressChart({ pools }: PoolProgressChartProps) {
  const data = pools
    .filter((p) => p.status === "open")
    .slice(0, 6)
    .map((p) => ({
      name: p.title.length > 16 ? p.title.slice(0, 16) + "…" : p.title,
      locked: p.current_locked_amount,
      remaining: Math.max(p.target_amount - p.current_locked_amount, 0),
      target: p.target_amount,
    }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-charcoal-soft">
        No active pools to display.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} barSize={28}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E8E0CE" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: "#3A362E" }}
          axisLine={{ stroke: "#E8E0CE" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#3A362E" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₦${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip
          formatter={(value: any, name: any) => [
            formatNaira(typeof value === 'number' ? value : 0),
            name === "locked" ? "Locked" : "Remaining",
          ]}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid #E8E0CE",
            fontSize: 13,
          }}
        />
        <Bar dataKey="locked" stackId="a" fill="#C9971F" radius={[0, 0, 0, 0]} />
        <Bar dataKey="remaining" stackId="a" fill="#F3ECDD" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}