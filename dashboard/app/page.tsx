"use client";

import { useEffect, useState } from "react";
import { listRuns } from "@/lib/api";
import { RunsFilter } from "@/components/RunsFilter";
import type { RunRecord } from "@/types/api";

export default function HomePage() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns(50)
      .then(setRuns)
      .catch(() => setError("Could not reach proxy at http://localhost:8080"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-12 text-center text-sm text-gray-400">Loading…</div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center text-sm text-red-500">{error}</div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Inference Runs</h1>
        <p className="text-sm text-gray-500 mt-1">{runs.length} run(s) recorded</p>
      </div>
      <RunsFilter runs={runs} />
    </div>
  );
}
