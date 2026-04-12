"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getDrift, getOutput, getRun } from "@/lib/api";
import type { DriftResult, OutputRecord, RunRecord } from "@/types/api";

function fmt(n: number | null, decimals = 1): string {
  return n != null ? n.toFixed(decimals) : "—";
}

function RunCard({
  run,
  output,
}: {
  run: RunRecord;
  output: OutputRecord | null;
}) {
  return (
    <div className="flex-1 min-w-0 rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-3 truncate">
        {run.run_id.slice(0, 8)} · {run.model}
      </h2>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-gray-500">Backend</dt>
        <dd>{run.backend}</dd>
        <dt className="text-gray-500">TTFT</dt>
        <dd>{fmt(run.ttft_ms)} ms</dd>
        <dt className="text-gray-500">TPS</dt>
        <dd>{fmt(run.tps, 2)}</dd>
        <dt className="text-gray-500">Tokens</dt>
        <dd>{run.token_count ?? "—"}</dd>
        <dt className="text-gray-500">Quality</dt>
        <dd>
          {run.quality_score != null ? run.quality_score.toFixed(3) : "—"}
        </dd>
      </dl>
      {output && (
        <div className="mt-4">
          <p className="text-xs text-gray-400 mb-1">Output</p>
          <p className="text-sm text-gray-800 whitespace-pre-wrap line-clamp-10">
            {output.full_text}
          </p>
        </div>
      )}
    </div>
  );
}

function DriftBadge({ result }: { result: DriftResult }) {
  const pct = (result.cosine_drift * 100).toFixed(1);
  return (
    <div
      className={`rounded-lg border p-4 text-center ${
        result.is_significant
          ? "border-amber-300 bg-amber-50"
          : "border-green-200 bg-green-50"
      }`}
    >
      <p className="text-xs font-medium text-gray-500 mb-1">Cosine Drift</p>
      <p
        className={`text-3xl font-bold tabular-nums ${
          result.is_significant ? "text-amber-600" : "text-green-600"
        }`}
      >
        {pct}%
      </p>
      <p className="text-xs mt-1 font-medium">
        {result.is_significant
          ? "Significant drift detected"
          : "Within normal range"}
      </p>
    </div>
  );
}

function ComparePageInner() {
  const searchParams = useSearchParams();
  const idA = searchParams.get("a");
  const idB = searchParams.get("b");

  const [runA, setRunA] = useState<RunRecord | null>(null);
  const [runB, setRunB] = useState<RunRecord | null>(null);
  const [outputA, setOutputA] = useState<OutputRecord | null>(null);
  const [outputB, setOutputB] = useState<OutputRecord | null>(null);
  const [drift, setDrift] = useState<DriftResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!idA || !idB) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getRun(idA).catch(() => null),
      getRun(idB).catch(() => null),
      getOutput(idA),
      getOutput(idB),
      getDrift(idA, idB),
    ])
      .then(([ra, rb, oa, ob, d]) => {
        if (!ra || !rb) {
          setError("One or both run IDs not found.");
          return;
        }
        setRunA(ra);
        setRunB(rb);
        setOutputA(oa);
        setOutputB(ob);
        setDrift(d);
      })
      .catch(() => setError("Failed to load runs."))
      .finally(() => setLoading(false));
  }, [idA, idB]);

  if (!idA || !idB) {
    return (
      <div className="py-12 text-center text-gray-500 text-sm">
        <p>
          Pass{" "}
          <code className="font-mono">
            ?a=&lt;run_id&gt;&amp;b=&lt;run_id&gt;
          </code>{" "}
          to compare two runs.
        </p>
        <p className="mt-2">
          <a href="/" className="text-blue-600 hover:underline">
            ← Back to runs
          </a>
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="py-12 text-center text-sm text-gray-400">Loading…</div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center text-sm text-red-500">
        {error}
        <p className="mt-2">
          <a href="/" className="text-blue-600 hover:underline">
            ← Back to runs
          </a>
        </p>
      </div>
    );
  }

  if (!runA || !runB) return null;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Run Comparison</h1>
        <a href="/" className="text-sm text-blue-600 hover:underline">
          ← Back to runs
        </a>
      </div>

      {drift && (
        <div className="mb-6 max-w-xs">
          <DriftBadge result={drift} />
        </div>
      )}

      <div className="flex gap-4">
        <RunCard run={runA} output={outputA} />
        <RunCard run={runB} output={outputB} />
      </div>
    </div>
  );
}

export default function RunComparePage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-sm text-gray-400">
          Loading…
        </div>
      }
    >
      <ComparePageInner />
    </Suspense>
  );
}
