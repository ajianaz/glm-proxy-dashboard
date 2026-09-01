import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { HistoryPoint, SamplePoint } from "./types";

interface DashDB extends DBSchema {
  windows: {
    key: string;
    value: HistoryPoint;
    indexes: { "by-window-start": string };
  };
  samples: {
    key: string;
    value: SamplePoint;
    indexes: { "by-captured-at": string };
  };
}

const DB_NAME = "glm-dash";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<DashDB>> | null = null;

function getDB(): Promise<IDBPDatabase<DashDB>> {
  if (!dbPromise) {
    dbPromise = openDB<DashDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("windows")) {
          const store = db.createObjectStore("windows", { keyPath: "key" });
          store.createIndex("by-window-start", "window_start");
        }
        if (!db.objectStoreNames.contains("samples")) {
          const store = db.createObjectStore("samples", { keyPath: "key" });
          store.createIndex("by-captured-at", "captured_at");
        }
      },
    });
  }
  return dbPromise;
}

/**
 * Record one poll:
 * - samples store keeps every poll (source for the intra-window accumulation curve)
 * - windows store keeps one row per rolling window, updated in place (history table)
 */
export async function recordPoll(
  sample: Omit<SamplePoint, "key">
): Promise<void> {
  const db = await getDB();
  const windowRow: HistoryPoint = {
    key: sample.window_start,
    window_start: sample.window_start,
    window_end: sample.window_end,
    tokens_used: sample.tokens_used,
    requests: sample.requests,
    captured_at: sample.captured_at,
  };
  const existing = await db.get("windows", windowRow.key);
  if (existing) {
    // monotonic guard: never record a decrease within the same window
    windowRow.tokens_used = Math.max(existing.tokens_used, sample.tokens_used);
    windowRow.requests = Math.max(existing.requests, sample.requests);
    windowRow.captured_at = sample.captured_at;
  }
  await db.put("windows", windowRow);
  await db.put("samples", {
    ...sample,
    key: `${sample.window_start}|${sample.captured_at}`,
  });
}

/** Window rows, newest first, capped to `limit`. */
export async function getWindows(limit = 60): Promise<HistoryPoint[]> {
  const db = await getDB();
  const all = await db.getAllFromIndex("windows", "by-window-start");
  return all.reverse().slice(0, limit);
}

/** Poll samples of one window (by window_start), chronological. */
export async function getSamples(windowStart: string): Promise<SamplePoint[]> {
  const db = await getDB();
  const all = await db.getAllFromIndex("samples", "by-captured-at");
  return all.filter((s) => s.window_start === windowStart);
}

/** Housekeeping: windows older than 30 days, samples older than 24h. */
export async function prune(): Promise<void> {
  const db = await getDB();
  const winCutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
  const smpCutoff = Date.now() - 24 * 60 * 60 * 1000;

  const windows = await db.getAllFromIndex("windows", "by-window-start");
  const wtx = db.transaction("windows", "readwrite");
  for (const w of windows) {
    if (new Date(w.window_start).getTime() < winCutoff) await wtx.store.delete(w.key);
  }
  await wtx.done;

  const samples = await db.getAllFromIndex("samples", "by-captured-at");
  const stx = db.transaction("samples", "readwrite");
  for (const s of samples) {
    if (new Date(s.captured_at).getTime() < smpCutoff) await stx.store.delete(s.key);
  }
  await stx.done;
}

/** Wipe all local data (used when the API key changes). */
export async function clearAll(): Promise<void> {
  const db = await getDB();
  await db.clear("windows");
  await db.clear("samples");
}
