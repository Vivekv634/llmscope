import type {
  DriftResult,
  OutputRecord,
  RunRecord,
  SignalResponse,
  TokenRecord,
} from "@/types/api";

const BASE = "http://localhost:8080";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error ${res.status} for ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function listModels(): Promise<string[]> {
  return apiFetch<string[]>("/api/models");
}

export interface RunsFilter {
  limit?: number;
  model?: string;
  tag?: string;
  q?: string;
}

export async function listRuns(filter: RunsFilter = {}): Promise<RunRecord[]> {
  const { limit = 50, model, tag, q } = filter;
  const params = new URLSearchParams({ limit: String(limit) });
  if (model) params.set("model", model);
  if (tag) params.set("tag", tag);
  if (q) params.set("q", q);
  return apiFetch<RunRecord[]>(`/api/runs?${params.toString()}`);
}

export async function listTags(): Promise<string[]> {
  return apiFetch<string[]>("/api/tags");
}

export async function getRun(runId: string): Promise<RunRecord> {
  return apiFetch<RunRecord>(`/api/runs/${runId}`);
}

export async function getTokens(runId: string): Promise<TokenRecord[]> {
  return apiFetch<TokenRecord[]>(`/api/runs/${runId}/tokens`);
}

export async function getOutput(runId: string): Promise<OutputRecord | null> {
  try {
    return await apiFetch<OutputRecord>(`/api/runs/${runId}/output`);
  } catch {
    return null;
  }
}

export async function getSignals(runId: string): Promise<SignalResponse | null> {
  try {
    return await apiFetch<SignalResponse>(`/api/runs/${runId}/signals`);
  } catch {
    return null;
  }
}

export async function getDrift(
  runId: string,
  compareTo: string
): Promise<DriftResult | null> {
  try {
    return await apiFetch<DriftResult>(
      `/api/runs/${runId}/drift?compare_to=${encodeURIComponent(compareTo)}`
    );
  } catch {
    return null;
  }
}

export function wsUrl(runId: string): string {
  return `ws://localhost:8080/ws/stream/${runId}`;
}

export const COMPARE_URL = `${BASE}/api/compare`;
