import { getOutput, getRun, getSignals, getTokens } from "@/lib/api";
import { LatencyTimeline } from "@/components/LatencyTimeline";
import { QualityScore } from "@/components/QualityScore";
import { LiveFeed } from "@/components/LiveFeed";
import type { LatencyPoint } from "@/types/api";

export default async function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [run, tokens, output, signals] = await Promise.all([
    getRun(id),
    getTokens(id),
    getOutput(id),
    getSignals(id),
  ]);

  const latencyPoints: LatencyPoint[] = tokens.map((t, i) => ({
    pos: t.position,
    gap_ms:
      i === 0 ? t.arrived_at_ms : t.arrived_at_ms - tokens[i - 1].arrived_at_ms,
    is_stall: signals?.latency.stall_positions.includes(t.position) ?? false,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold font-mono">{run.run_id}</h1>
        <p className="text-sm text-gray-500 mt-1">
          {run.model} · {run.backend} ·{" "}
          {new Date(run.created_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="TTFT" value={run.ttft_ms != null ? `${run.ttft_ms.toFixed(0)} ms` : "—"} />
        <Stat label="Total" value={run.total_ms != null ? `${run.total_ms.toFixed(0)} ms` : "—"} />
        <Stat label="TPS" value={run.tps != null ? run.tps.toFixed(2) : "—"} />
        <Stat label="Tokens" value={run.token_count?.toString() ?? "—"} />
      </div>

      {signals && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h2 className="text-sm font-medium text-gray-500 mb-3">
              Latency Timeline
            </h2>
            <LatencyTimeline points={latencyPoints} />
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h2 className="text-sm font-medium text-gray-500 mb-3">
              Quality Score
            </h2>
            <QualityScore result={signals.quality} />
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 mb-3">
          Live Token Feed
        </h2>
        <LiveFeed runId={run.run_id} staticText={output?.full_text ?? null} />
      </div>

      {output && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h2 className="text-sm font-medium text-gray-500 mb-3">
            Full Output
          </h2>
          <pre className="text-sm whitespace-pre-wrap leading-relaxed">
            {output.full_text}
          </pre>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold mt-1">{value}</p>
    </div>
  );
}
