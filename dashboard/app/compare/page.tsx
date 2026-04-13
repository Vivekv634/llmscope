"use client";

import { useEffect, useRef, useState } from "react";
import { COMPARE_URL, listModels } from "@/lib/api";
import { ModelToggle } from "@/components/ModelToggle";

interface CompareApiResult {
  model: string;
  ttft_ms: number;
  total_ms: number;
  token_count: number;
  tps: number;
  quality: { entropy_score: number; token_count: number };
  output: string;
}

type ModelStatus = "idle" | "generating" | "done" | "error";

interface ModelState {
  status: ModelStatus;
  result: CompareApiResult | null;
  error: string | null;
}

function statusBadge(status: ModelStatus) {
  if (status === "generating") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
        generating
      </span>
    );
  }
  if (status === "done") {
    return (
      <span className="text-xs font-medium text-green-600">done</span>
    );
  }
  if (status === "error") {
    return (
      <span className="text-xs font-medium text-red-500">error</span>
    );
  }
  return <span className="text-xs text-gray-400">idle</span>;
}

function ModelCard({ model, state }: { model: string; state: ModelState }) {
  const { status, result, error } = state;

  return (
    <div
      className={`rounded-lg border bg-white p-5 flex flex-col gap-3 transition-colors ${
        status === "generating"
          ? "border-indigo-300"
          : status === "done"
          ? "border-green-200"
          : status === "error"
          ? "border-red-200"
          : "border-gray-200"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm truncate">{model}</span>
        {statusBadge(status)}
      </div>

      {status === "generating" && (
        <div className="space-y-2">
          <div className="h-2 bg-gray-100 rounded animate-pulse" />
          <div className="h-2 bg-gray-100 rounded animate-pulse w-3/4" />
        </div>
      )}

      {status === "error" && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      {status === "done" && result && (
        <>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-gray-500">TTFT</dt>
            <dd className="tabular-nums">{result.ttft_ms.toFixed(0)} ms</dd>
            <dt className="text-gray-500">Total</dt>
            <dd className="tabular-nums">{result.total_ms.toFixed(0)} ms</dd>
            <dt className="text-gray-500">TPS</dt>
            <dd className="tabular-nums">{result.tps.toFixed(2)}</dd>
            <dt className="text-gray-500">Tokens</dt>
            <dd className="tabular-nums">{result.token_count}</dd>
            <dt className="text-gray-500">Quality</dt>
            <dd className="tabular-nums">{result.quality.entropy_score.toFixed(3)}</dd>
          </dl>
          <div className="border-t border-gray-100 pt-3">
            <p className="text-xs text-gray-400 mb-1">Output</p>
            <p className="text-sm text-gray-800 whitespace-pre-wrap break-words line-clamp-6">
              {result.output}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<string>("");
  const [states, setStates] = useState<Record<string, ModelState>>({});
  const [running, setRunning] = useState(false);
  const abortRefs = useRef<Record<string, AbortController>>({});

  useEffect(() => {
    listModels()
      .then(setAvailableModels)
      .catch(() => setAvailableModels([]));
  }, []);

  const inFlight = Object.values(states).filter(
    (s) => s.status === "generating"
  ).length;

  function setModelState(model: string, patch: Partial<ModelState>) {
    setStates((prev) => ({
      ...prev,
      [model]: { ...prev[model], ...patch },
    }));
  }

  async function runModel(model: string, ctrl: AbortController) {
    setModelState(model, { status: "generating", result: null, error: null });
    try {
      const res = await fetch(COMPARE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, models: [model] }),
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error(`server error ${res.status}`);
      const data = (await res.json()) as CompareApiResult[];
      setModelState(model, { status: "done", result: data[0] });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setModelState(model, {
        status: "error",
        error: err instanceof Error ? err.message : "unknown error",
      });
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!prompt || selectedModels.length === 0) return;

    Object.values(abortRefs.current).forEach((c) => c.abort());
    abortRefs.current = {};

    const initial: Record<string, ModelState> = {};
    for (const m of selectedModels) {
      initial[m] = { status: "idle", result: null, error: null };
    }
    setStates(initial);
    setRunning(true);

    await Promise.all(
      selectedModels.map((m) => {
        const ctrl = new AbortController();
        abortRefs.current[m] = ctrl;
        return runModel(m, ctrl);
      })
    );

    setRunning(false);
  }

  const hasResults = Object.values(states).some((s) => s.status !== "idle");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Model Comparator</h1>
        {running && inFlight > 0 && (
          <span className="text-sm text-indigo-600 font-medium">
            {inFlight} of {selectedModels.length} generating…
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 max-w-2xl">
        <div>
          <label className="block text-sm font-medium mb-2">
            Available Models
            {selectedModels.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                {selectedModels.length} selected
              </span>
            )}
          </label>
          <ModelToggle
            models={availableModels}
            selected={selectedModels}
            onChange={setSelectedModels}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="prompt">
            Prompt
          </label>
          <textarea
            id="prompt"
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your prompt…"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>

        <button
          type="submit"
          disabled={running || selectedModels.length === 0 || !prompt}
          className="px-5 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {running ? `Running (${inFlight} left)…` : `Compare${selectedModels.length > 0 ? ` (${selectedModels.length})` : ""}`}
        </button>
      </form>

      {hasResults && (
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${Math.min(selectedModels.length, 3)}, minmax(0, 1fr))`,
          }}
        >
          {selectedModels.map((m) => (
            <ModelCard key={m} model={m} state={states[m] ?? { status: "idle", result: null, error: null }} />
          ))}
        </div>
      )}
    </div>
  );
}
