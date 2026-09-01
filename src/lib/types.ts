// Types mirroring glm-proxy-golang public API (GET /stats response).
// Source: internal/storage/types.go @ ajianaz/glm-proxy-golang main

export interface CurrentUsage {
  tokens_used_in_current_window: number;
  window_started_at: string;
  window_ends_at: string;
  remaining_tokens: number;
}

export interface StatsResponse {
  key: string;
  name: string;
  model: string;
  token_limit_per_5h: number;
  expiry_date: string;
  created_at: string;
  last_used: string;
  is_expired: boolean;
  current_usage: CurrentUsage;
  total_requests: number;
  total_lifetime_tokens: number;
}

// Client-side data stored in IndexedDB (accumulated from /stats polls)

/** One rolling window (5h): one row, updated in place while the window is live. */
export interface HistoryPoint {
  key: string; // = window_start, primary key in the IndexedDB store
  window_start: string; // ISO timestamp
  window_end: string; // ISO timestamp
  tokens_used: number;
  requests: number;
  captured_at: string; // ISO timestamp of the last poll for this window
}

/** One /stats poll: raw sample for the intra-window accumulation curve. */
export interface SamplePoint {
  key: string; // = window_start|captured_at, primary key in the IndexedDB store
  window_start: string;
  window_end: string;
  tokens_used: number; // cumulative within the window at poll time
  requests: number;
  captured_at: string;
}
