import type { StatsResponse } from "./types";

const STORAGE_KEY = "glm-dash.apikey";
const DEFAULT_BASE = "https://glm.ajianaz.dev";

/** Read the stored API key from localStorage, or null when absent. */
export function getApiKey(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

/** Persist the API key to localStorage. */
export function setApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key);
}

/** Remove the stored API key (logout). */
export function clearApiKey(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/** Resolve the /stats base URL (VITE_API_BASE override, prod default). */
export function getBaseUrl(): string {
  // Configurable for local development against a local proxy instance
  return import.meta.env.VITE_API_BASE ?? DEFAULT_BASE;
}

export interface RateLimitInfo {
  tokens_used: number;
  tokens_limit: number;
  window_ends_at: string;
}

/** Coerce an unknown JSON value to a finite number, 0 when absent/invalid. */
function toFiniteNumber(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

export type StatsError =
  | { kind: "unauthorized" } // 401: key invalid
  | { kind: "forbidden"; expiryDate?: string } // 403: key expired
  | { kind: "rate_limited"; rateLimit: RateLimitInfo } // 429: 5h window quota exhausted, resets at window_ends_at
  | { kind: "network" }
  | { kind: "unknown"; status: number };

/**
 * Fetch /stats for the given key and map every outcome to a discriminated
 * result: ok + StatsResponse, or a typed error (401 invalid, 403 expired,
 * 429 quota with RateLimitInfo, network failure, unknown status).
 */
export async function fetchStats(apiKey: string): Promise<
  { ok: true; data: StatsResponse } | { ok: false; error: StatsError }
> {
  const url = `${getBaseUrl()}/stats`;
  let resp: Response;
  try {
    resp = await fetch(url, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "x-api-key": apiKey,
      },
    });
  } catch {
    return { ok: false, error: { kind: "network" } };
  }

  if (resp.status === 401) return { ok: false, error: { kind: "unauthorized" } };
  if (resp.status === 429) {
    // 429 = 5h window quota exhausted, key itself is still valid.
    // Body carries tokens_used / tokens_limit / window_ends_at. Sanitize every
    // field: older/partial bodies may omit numerics, and undefined leaking into
    // components would break toLocaleString rendering.
    let rateLimit: RateLimitInfo | undefined;
    try {
      const body = (await resp.json()) as { error?: Record<string, unknown> };
      const e = body.error;
      if (e && typeof e.window_ends_at === "string" && e.window_ends_at) {
        rateLimit = {
          tokens_used: toFiniteNumber(e.tokens_used),
          tokens_limit: toFiniteNumber(e.tokens_limit),
          window_ends_at: e.window_ends_at,
        };
      }
    } catch {
      // body not JSON; keep undefined
    }
    return {
      ok: false,
      error: {
        kind: "rate_limited",
        rateLimit: rateLimit ?? { tokens_used: 0, tokens_limit: 0, window_ends_at: "" },
      },
    };
  }
  if (resp.status === 403) {
    // expired key returns { "error": "API key expired on <date>" }
    let expiryDate: string | undefined;
    try {
      const body = (await resp.json()) as { error?: string };
      const m = body.error?.match(/expired on (.+)$/);
      if (m) expiryDate = m[1];
    } catch {
      // body not JSON; keep undefined
    }
    return { ok: false, error: { kind: "forbidden", expiryDate } };
  }
  if (!resp.ok) return { ok: false, error: { kind: "unknown", status: resp.status } };

  const data = (await resp.json()) as StatsResponse;
  return { ok: true, data };
}
