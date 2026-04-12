"use client";

import { useState, useMemo } from "react";
import type { RunRecord } from "@/types/api";
import { RunList } from "@/components/RunList";

interface RunsFilterProps {
  runs: RunRecord[];
}

export function RunsFilter({ runs }: RunsFilterProps) {
  const models = useMemo(() => {
    const set = new Set(runs.map((r) => r.model));
    return Array.from(set).sort();
  }, [runs]);

  const [selected, setSelected] = useState<string | null>(null);

  const filtered = selected == null ? runs : runs.filter((r) => r.model === selected);

  function toggle(model: string) {
    setSelected((prev) => (prev === model ? null : model));
  }

  return (
    <div>
      {models.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {models.map((m) => (
            <button
              key={m}
              onClick={() => toggle(m)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                selected === m
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400"
              }`}
            >
              {m}
            </button>
          ))}
          {selected !== null && (
            <button
              onClick={() => setSelected(null)}
              className="px-3 py-1 rounded-full text-sm border border-gray-200 text-gray-500 hover:border-gray-400"
            >
              clear
            </button>
          )}
        </div>
      )}
      <RunList runs={filtered} />
    </div>
  );
}
