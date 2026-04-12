"use client";

import { useEffect, useState } from "react";
import { COMPARE_URL, listModels } from "@/lib/api";
import { ModelToggle } from "@/components/ModelToggle";
import type { CompareRow } from "@/components/ModelComparator";
import { ModelComparator } from "@/components/ModelComparator";

interface CompareApiResult {
  model: string;
  ttft_ms: number;
  total_ms: number;
  token_count: number;
  tps: number;
  quality: { entropy_score: number; token_count: number };
  output: string;
}

export default function ComparePage() {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<string>("");
  const [results, setResults] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listModels()
      .then(setAvailableModels)
      .catch(() => setAvailableModels([]));
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!prompt || selectedModels.length === 0) return;

    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const res = await fetch(COMPARE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, models: selectedModels }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = (await res.json()) as CompareApiResult[];
      setResults(
        data.map((r) => ({
          model: r.model,
          ttft_ms: r.ttft_ms,
          tps: r.tps,
          token_count: r.token_count,
          entropy_score: r.quality.entropy_score,
          output: r.output,
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Model Comparator</h1>

      <form onSubmit={handleSubmit} className="space-y-5 max-w-2xl">
        <div>
          <label className="block text-sm font-medium mb-2">
            Available Models
            {availableModels.length > 0 && (
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
          disabled={loading || selectedModels.length === 0 || !prompt}
          className="px-5 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "Running…" : `Compare ${selectedModels.length > 0 ? `(${selectedModels.length})` : ""}`}
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {results.length > 0 && <ModelComparator rows={results} />}
    </div>
  );
}
