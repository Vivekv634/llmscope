import type { RunRecord } from "@/types/api";

function fmt(n: number | null, decimals = 1): string {
  return n != null ? n.toFixed(decimals) : "—";
}

export function RunList({ runs }: { runs: RunRecord[] }) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-12 text-center">
        No runs yet. Send a request through the proxy to record your first run.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-4 py-3">Run ID</th>
            <th className="px-4 py-3">Model</th>
            <th className="px-4 py-3">Backend</th>
            <th className="px-4 py-3 text-right">TTFT (ms)</th>
            <th className="px-4 py-3 text-right">TPS</th>
            <th className="px-4 py-3 text-right">Tokens</th>
            <th className="px-4 py-3 text-right">Quality</th>
            <th className="px-4 py-3">Created</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.run_id}
              className="border-b border-gray-100 last:border-0 hover:bg-gray-50"
            >
              <td className="px-4 py-3">
                <a
                  href={`/runs/${run.run_id}`}
                  className="font-mono text-blue-600 hover:underline"
                >
                  {run.run_id.slice(0, 8)}
                </a>
              </td>
              <td className="px-4 py-3 font-medium">{run.model}</td>
              <td className="px-4 py-3 text-gray-500">{run.backend}</td>
              <td className="px-4 py-3 text-right tabular-nums">
                {fmt(run.ttft_ms)}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {fmt(run.tps, 2)}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {run.token_count ?? "—"}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {run.quality_score != null
                  ? run.quality_score.toFixed(3)
                  : "—"}
              </td>
              <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                {new Date(run.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
