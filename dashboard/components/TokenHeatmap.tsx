"use client";

import type { LatencyPoint } from "@/types/api";

interface TokenHeatmapProps {
  points: LatencyPoint[];
  tokens: string[];
}

function tokenClass(gap_ms: number, is_stall: boolean): string {
  if (is_stall) {
    return "bg-red-100 text-red-900 rounded px-0.5";
  }
  if (gap_ms > 200) {
    return "bg-amber-100 text-amber-900 rounded px-0.5";
  }
  if (gap_ms > 80) {
    return "bg-yellow-50 text-yellow-900 rounded px-0.5";
  }
  return "text-gray-800";
}

function Legend() {
  return (
    <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-3 rounded bg-gray-200" />
        fast
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-3 rounded bg-yellow-50 border border-yellow-200" />
        slow (&gt;80 ms)
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-3 rounded bg-amber-100" />
        very slow (&gt;200 ms)
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-3 rounded bg-red-100" />
        stall
      </span>
    </div>
  );
}

export function TokenHeatmap({ points, tokens }: TokenHeatmapProps) {
  if (points.length === 0 || tokens.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4 text-center">No token data</p>
    );
  }

  return (
    <div>
      <Legend />
      <p className="text-sm leading-7 break-words whitespace-pre-wrap">
        {points.map((p, i) => {
          const text = tokens[i] ?? "";
          const cls = tokenClass(p.gap_ms, p.is_stall);
          const title = `#${p.pos} — ${p.gap_ms.toFixed(1)} ms${p.is_stall ? " (stall)" : ""}`;
          return (
            <span key={p.pos} className={cls} title={title}>
              {text}
            </span>
          );
        })}
      </p>
    </div>
  );
}
