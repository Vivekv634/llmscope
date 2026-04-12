"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getOutput, getRun, getSignals, getTokens } from "@/lib/api";
import { LatencyTimeline } from "@/components/LatencyTimeline";
import { LiveFeed } from "@/components/LiveFeed";
import { QualityScore } from "@/components/QualityScore";
import { TagEditor } from "@/components/TagEditor";
import type {
  LatencyPoint,
  OutputRecord,
  RunRecord,
  SignalResponse,
  TokenRecord,
} from "@/types/api";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold mt-1">{value}</p>
    </div>
  );
}

function RunDetail({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunRecord | null>(null);
  const [tokens, setTokens] = useState<TokenRecord[]>([]);
  const [output, setOutput] = useState<OutputRecord | null>(null);
  const [signals, setSignals] = useState<SignalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getRun(runId),
      getTokens(runId),
      getOutput(runId),
      getSignals(runId),
    ])
      .then(([r, t, o, s]) => {
        setRun(r);
        setTokens(t);
        setOutput(o);
        setSignals(s);
      })
      .catch(() => setError("Run not found or proxy unreachable."))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="py-12 text-center text-sm text-gray-400">Loading…</div>
    );
  }

  if (error || !run) {
    return (
      <div className="py-12 text-center text-sm text-red-500">
        {error ?? "Run not found."}
      </div>
    );
  }

  const latencyPoints: LatencyPoint[] = tokens.map((t, i) => ({
    pos: t.position,
    gap_ms:
      i === 0 ? t.arrived_at_ms : t.arrived_at_ms - tokens[i - 1].arrived_at_ms,
    is_stall: signals?.latency.stall_positions.includes(t.position) ?? false,
  }));

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold font-mono">{run.run_id}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {run.model} · {run.backend} ·{" "}
            {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
        <a href="/" className="text-sm text-blue-600 hover:underline">
          ← Back to runs
        </a>
      </div>

      <div className="flex items-start gap-3 flex-wrap">
        <TagEditor runId={run.run_id} initialTags={run.tags} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat
          label="TTFT"
          value={run.ttft_ms != null ? `${run.ttft_ms.toFixed(0)} ms` : "—"}
        />
        <Stat
          label="Total"
          value={run.total_ms != null ? `${run.total_ms.toFixed(0)} ms` : "—"}
        />
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
          <pre className="text-sm whitespace-pre-wrap break-words leading-relaxed overflow-hidden">
            {output.full_text}
          </pre>
        </div>
      )}
    </div>
  );
}

function RunPageInner() {
  const searchParams = useSearchParams();
  const runId = searchParams.get("id");

  if (!runId) {
    return (
      <div className="py-12 text-center text-sm text-gray-500">
        No run ID provided. Pass{" "}
        <code className="font-mono">?id=&lt;run_id&gt;</code> in the URL.
      </div>
    );
  }

  return <RunDetail runId={runId} />;
}

export default function RunPage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-sm text-gray-400">
          Loading…
        </div>
      }
    >
      <RunPageInner />
    </Suspense>
  );
}
