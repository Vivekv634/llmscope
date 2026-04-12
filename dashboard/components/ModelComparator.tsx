export interface CompareRow {
  model: string;
  ttft_ms: number;
  tps: number;
  token_count: number;
  entropy_score: number;
  output: string;
}

function fmt(n: number, d = 2): string {
  return n.toFixed(d);
}

export function ModelComparator({ rows }: { rows: CompareRow[] }) {
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3 text-right">TTFT (ms)</th>
              <th className="px-4 py-3 text-right">TPS</th>
              <th className="px-4 py-3 text-right">Tokens</th>
              <th className="px-4 py-3 text-right">Entropy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.model}
                className="border-b border-gray-100 last:border-0 hover:bg-gray-50"
              >
                <td className="px-4 py-3 font-medium">{r.model}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {fmt(r.ttft_ms, 1)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {fmt(r.tps)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {r.token_count}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {fmt(r.entropy_score, 4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {rows.map((r) => (
          <div
            key={r.model}
            className="bg-white border border-gray-200 rounded-lg p-4"
          >
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              {r.model}
            </p>
            <pre className="text-sm whitespace-pre-wrap leading-relaxed text-gray-700 max-h-48 overflow-y-auto">
              {r.output}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
