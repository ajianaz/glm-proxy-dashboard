import type { StatsResponse } from "./types";

const STORAGE_KEY = "glm-dash.apikey";
const DEFAULT_BASE = "https://glm.ajianaz.dev";

export function getApiKey(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

export function setApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key);
}

export function clearApiKey(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getBaseUrl(): string {
  // Configurable for local development against a local proxy instance
  return import.meta.env.VITE_API_BASE ?? DEFAULT_BASE;
}

export interface RateLimitInfo {
  tokens_used: number;
  tokens_limit: number;
  window_ends_at: string;
}

export type StatsError =
  | { kind: "unauthorized" } // 401: key invalid
  | { kind: "forbidden"; expiryDate?: string } // 403: key expired
  | { kind: "rate_limited"; rateLimit: RateLimitInfo } // 429: 5h window quota exhausted, resets at window_ends_at
  | { kind: "network" }
  | { kind: "unknown"; status: number };

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
    // Body carries tokens_used / tokens_limit / window_ends_at.
    let rateLimit: RateLimitInfo | undefined;
    try {
      const body = (await resp.json()) as { error?: RateLimitInfo };
      if (body.error && body.error.window_ends_at) rateLimit = body.error;
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
