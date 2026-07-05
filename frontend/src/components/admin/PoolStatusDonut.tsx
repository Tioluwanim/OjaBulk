"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { PoolResponse } from "@/lib/types";

interface PoolStatusDonutProps {
  pools: PoolResponse[];
}

const COLORS: Record<string, string> = {
  open: "#C9971F",
  fulfilled: "#2F7D5A",
  refunded: "#B33A3A",
};

const LABELS: Record<string, string> = {
  open: "Open",
  fulfilled: "Fulfilled",
  refunded: "Refunded",
};

export function PoolStatusDonut({ pools }: PoolStatusDonutProps) {
  const counts = pools.reduce<Record<string, number>>((acc, p) => {
    acc[p.status] = (acc[p.status] ?? 0) + 1;
    return acc;
  }, {});

  const data = Object.entries(counts).map(([status, count]) => ({
    name: LABELS[status] ?? status,
    value: count,
    status,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-charcoal-soft">
        No pools yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={65}
          outerRadius={95}
          paddingAngle={3}
        >
          {data.map((entry) => (
            <Cell key={entry.status} fill={COLORS[entry.status] ?? "#999"} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid #E8E0CE",
            fontSize: 13,
          }}
        />
        <Legend
          verticalAlign="bottom"
          iconType="circle"
          wrapperStyle={{ fontSize: 12, color: "#3A362E" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}