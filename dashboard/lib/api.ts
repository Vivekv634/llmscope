import type {
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

export async function listRuns(limit = 50): Promise<RunRecord[]> {
  return apiFetch<RunRecord[]>(`/api/runs?limit=${limit}`);
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

export function wsUrl(runId: string): string {
  return `ws://localhost:8080/ws/stream/${runId}`;
}

export const COMPARE_URL = `${BASE}/api/compare`;
