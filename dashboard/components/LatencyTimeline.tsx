"use client";

import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LatencyPoint } from "@/types/api";

export function LatencyTimeline({ points }: { points: LatencyPoint[] }) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-8 text-center">No token data</p>
    );
  }

  const stalls = points.filter((p) => p.is_stall).map((p) => p.pos);

  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <XAxis
          dataKey="pos"
          tick={{ fontSize: 11 }}
          label={{ value: "Token position", position: "insideBottom", offset: -2, fontSize: 11 }}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          label={{ value: "Gap (ms)", angle: -90, position: "insideLeft", fontSize: 11 }}
        />
        <Tooltip
          formatter={(v: number) => [`${v.toFixed(1)} ms`, "Gap"]}
          labelFormatter={(l: number) => `Token #${l}`}
        />
        <Area
          type="monotone"
          dataKey="gap_ms"
          stroke="#6366f1"
          fill="#e0e7ff"
          strokeWidth={1.5}
          dot={false}
        />
        {stalls.map((pos) => (
          <ReferenceLine
            key={pos}
            x={pos}
            stroke="#ef4444"
            strokeDasharray="3 3"
            label={{ value: "stall", fontSize: 10, fill: "#ef4444" }}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
