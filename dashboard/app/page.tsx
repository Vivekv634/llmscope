"use client";

import { useEffect, useState } from "react";
import { listRuns } from "@/lib/api";
import { RunsFilter } from "@/components/RunsFilter";

export default function HomePage() {
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns({ limit: 200 })
      .then((runs) => setTotalCount(runs.length))
      .catch(() => setError("Could not reach proxy at http://localhost:8080"));
  }, []);

  if (error) {
    return (
      <div className="py-12 text-center text-sm text-red-500">{error}</div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Inference Runs</h1>
        {totalCount !== null && (
          <p className="text-sm text-gray-500 mt-1">{totalCount} run(s) recorded</p>
        )}
      </div>
      <RunsFilter initialCount={totalCount ?? 0} />
    </div>
  );
}
