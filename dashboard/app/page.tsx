import { listRuns } from "@/lib/api";
import { RunList } from "@/components/RunList";

export default async function HomePage() {
  const runs = await listRuns(50);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Inference Runs</h1>
        <p className="text-sm text-gray-500 mt-1">{runs.length} run(s) recorded</p>
      </div>
      <RunList runs={runs} />
    </div>
  );
}
