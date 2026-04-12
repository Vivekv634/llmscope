export interface RunRecord {
  run_id: string;
  model: string;
  backend: string;
  prompt_hash: string;
  prompt_text: string | null;
  created_at: string;
  ttft_ms: number | null;
  total_ms: number | null;
  token_count: number | null;
  tps: number | null;
  quality_score: number | null;
  tags: string[];
}

export interface TokenRecord {
  run_id: string;
  position: number;
  text: string;
  arrived_at_ms: number;
}

export interface OutputRecord {
  run_id: string;
  full_text: string;
  token_count: number;
}

export interface LatencyResult {
  ttft_ms: number;
  total_ms: number;
  tps: number;
  stall_positions: number[];
}

export interface QualityResult {
  entropy_score: number;
  token_count: number;
}

export interface SignalResponse {
  latency: LatencyResult;
  quality: QualityResult;
}

export interface WsTokenEvent {
  type: "token";
  run_id: string;
  position: number;
  text: string;
  arrived_at_ms: number;
}

export interface WsDoneEvent {
  type: "done";
  run_id: string;
  total_ms: number;
}

export interface WsPingEvent {
  type: "ping";
}

export type WsEvent = WsTokenEvent | WsDoneEvent | WsPingEvent;

export interface LatencyPoint {
  pos: number;
  gap_ms: number;
  is_stall: boolean;
}
