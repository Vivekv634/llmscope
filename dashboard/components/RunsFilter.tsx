"use client";

import { useEffect, useState, useCallback } from "react";
import { listRuns, listTags } from "@/lib/api";
import type { RunRecord } from "@/types/api";
import { RunList } from "@/components/RunList";

function Pill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-sm border transition-colors ${
        active
          ? "bg-indigo-600 text-white border-indigo-600"
          : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400"
      }`}
    >
      {label}
    </button>
  );
}

export function RunsFilter({ initialCount }: { initialCount: number }) {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [allModels, setAllModels] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [model, setModel] = useState<string | null>(null);
  const [tag, setTag] = useState<string | null>(null);
  const [q, setQ] = useState<string>("");
  const [debouncedQ, setDebouncedQ] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRuns({ limit: 200 })
      .then((all) => {
        const models = Array.from(new Set(all.map((r) => r.model))).sort();
        setAllModels(models);
      })
      .catch(() => {});
    listTags()
      .then(setAllTags)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const fetchRuns = useCallback(() => {
    setLoading(true);
    listRuns({
      limit: 50,
      model: model ?? undefined,
      tag: tag ?? undefined,
      q: debouncedQ || undefined,
    })
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, [model, tag, debouncedQ]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const hasFilter = model !== null || tag !== null || debouncedQ !== "";

  function clearAll() {
    setModel(null);
    setTag(null);
    setQ("");
  }

  return (
    <div>
      <div className="flex flex-col gap-3 mb-5">
        <div className="flex items-center gap-2">
          <input
            type="search"
            placeholder="Search prompt…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="text-sm border border-gray-300 rounded-md px-3 py-1.5 w-60 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          {hasFilter && (
            <button
              type="button"
              onClick={clearAll}
              className="text-sm text-gray-500 hover:text-gray-800 underline"
            >
              clear all
            </button>
          )}
        </div>

        {allModels.length > 1 && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-gray-400 uppercase tracking-wide w-10">
              model
            </span>
            {allModels.map((m) => (
              <Pill
                key={m}
                label={m}
                active={model === m}
                onClick={() => setModel((prev) => (prev === m ? null : m))}
              />
            ))}
          </div>
        )}

        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-gray-400 uppercase tracking-wide w-10">
              tag
            </span>
            {allTags.map((t) => (
              <Pill
                key={t}
                label={t}
                active={tag === t}
                onClick={() => setTag((prev) => (prev === t ? null : t))}
              />
            ))}
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-gray-400 py-8 text-center">Loading…</p>
      ) : (
        <>
          {hasFilter && (
            <p className="text-xs text-gray-400 mb-3">
              {runs.length} of {initialCount} run(s)
            </p>
          )}
          <RunList runs={runs} />
        </>
      )}
    </div>
  );
}
