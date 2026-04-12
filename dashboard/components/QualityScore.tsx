import type { QualityResult } from "@/types/api";

function scoreLabel(score: number): { label: string; color: string } {
  if (score >= 0.7) return { label: "High diversity", color: "text-green-600" };
  if (score >= 0.4) return { label: "Moderate diversity", color: "text-yellow-600" };
  return { label: "Low diversity", color: "text-red-500" };
}

export function QualityScore({ result }: { result: QualityResult }) {
  const pct = Math.round(result.entropy_score * 100);
  const { label, color } = scoreLabel(result.entropy_score);

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-3">
        <span className="text-4xl font-semibold tabular-nums">{pct}</span>
        <span className="text-gray-500 text-sm mb-1">/ 100 entropy</span>
      </div>

      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      <p className={`text-sm font-medium ${color}`}>{label}</p>
      <p className="text-xs text-gray-400">{result.token_count} tokens analysed</p>
    </div>
  );
}
