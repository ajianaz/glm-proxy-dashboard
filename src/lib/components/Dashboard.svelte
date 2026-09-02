<script lang="ts">
  import { onMount } from "svelte";
  import { fetchStats } from "../api";
  import { recordPoll, getWindows, getSamples, prune, clearAll } from "../db";
  import type { HistoryPoint, SamplePoint, StatsResponse } from "../types";
  import { formatCompact } from "../format";
  import WindowCard from "./WindowCard.svelte";
  import StatGrid from "./StatGrid.svelte";
  import AccumulationChart from "./AccumulationChart.svelte";
  import HistoryTable from "./HistoryTable.svelte";
  import Banner from "./Banner.svelte";

  let { apikey, ondisconnect }: { apikey: string; ondisconnect: () => void } = $props();

  const POLL_OPTIONS = [
    { value: 1, label: "Tiap 1 mnt" },
    { value: 5, label: "Tiap 5 mnt" },
    { value: 15, label: "Tiap 15 mnt" },
    { value: 30, label: "Tiap 30 mnt" },
    { value: 60, label: "Tiap 1 jam" },
  ]; // minutes
  const DEFAULT_POLL_MIN = 5;
  const POLL_MIN_KEY = "glm-dash.pollmin";

  let stats = $state<StatsResponse | null>(null);
  let windows = $state<HistoryPoint[]>([]);
  let samples = $state<SamplePoint[]>([]);
  let lastSync = $state<Date | null>(null);
  let failStreak = $state(0);
  let offline = $state(false);
  let loaded = $state(false);
  let timer: ReturnType<typeof setInterval> | undefined;
  let seq = 0;

  // 429 = key valid, 5h window quota exhausted. Keep showing the last good
  // snapshot plus the quota card with reset time; polling continues so the
  // dashboard recovers automatically once the window rolls.
  let rateLimited = $state<{ tokensUsed: number; tokensLimit: number; windowEndsAt: string } | null>(
    null,
  );

  const rlBody = $derived.by(() => {
    if (!rateLimited) return "";
    const used = formatCompact(rateLimited.tokensUsed);
    const limit = formatCompact(rateLimited.tokensLimit);
    const resetAt = rateLimited.windowEndsAt
      ? new Date(rateLimited.windowEndsAt).toLocaleTimeString("id-ID", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "setelah window bergeser";
    return `Key masih aktif, jatah terpakai ${used} dari ${limit} token (${rateLimited.tokensUsed.toLocaleString("id-ID")} / ${rateLimited.tokensLimit.toLocaleString("id-ID")}). Kuota kembali pada ${resetAt}, pantauan lanjut otomatis.`;
  });

  function loadPollMin(): number {
    const v = Number.parseInt(localStorage.getItem(POLL_MIN_KEY) ?? "", 10);
    return POLL_OPTIONS.some((o) => o.value === v) ? v : DEFAULT_POLL_MIN;
  }
  let pollMin = $state(loadPollMin());

  function setPollMin(e: Event) {
    const v = Number.parseInt((e.currentTarget as HTMLSelectElement).value, 10);
    if (!POLL_OPTIONS.some((o) => o.value === v)) return;
    pollMin = v;
    localStorage.setItem(POLL_MIN_KEY, String(v));
    startPolling(); // apply immediately
  }

  async function poll() {
    const reqId = ++seq;
    const res = await fetchStats(apikey);
    if (reqId !== seq) return; // stale response guard
    if (res.ok) {
      stats = res.data;
      rateLimited = null;
      offline = false;
      failStreak = 0;
      lastSync = new Date();
      await recordPoll({
        window_start: res.data.current_usage.window_started_at,
        window_end: res.data.current_usage.window_ends_at,
        tokens_used: res.data.current_usage.tokens_used_in_current_window,
        requests: res.data.total_requests,
        captured_at: lastSync.toISOString(),
      });
      windows = await getWindows();
      samples = await getSamples(res.data.current_usage.window_started_at);
    } else {
      failStreak += 1;
      // A non-429 failure invalidates the quota state: a 401/403 after a 429
      // must show the auth failure, not a stale "key masih aktif" banner.
      if (res.error.kind !== "rate_limited") rateLimited = null;
      // Network errors (kind === "network") flip the offline indicator;
      // auth errors surface via the banner below. 429 is not an error state:
      // the quota card keeps rendering with the server-provided reset time.
      offline = res.error.kind === "network";
      if (res.error.kind === "forbidden") {
        // expired: stop polling, keep snapshot
        stopPolling();
      } else if (res.error.kind === "rate_limited") {
        rateLimited = {
          tokensUsed: res.error.rateLimit.tokens_used,
          tokensLimit: res.error.rateLimit.tokens_limit,
          windowEndsAt: res.error.rateLimit.window_ends_at,
        };
      }
    }
  }

  function stopPolling() {
    if (timer) clearInterval(timer);
    timer = undefined;
    // Invalidate any in-flight poll: without this, a request already running
    // at logout/unmount passes the stale guard and writes the old key's data
    // into IndexedDB after clearAll().
    seq += 1;
  }

  function startPolling() {
    stopPolling();
    timer = setInterval(poll, pollMin * 60_000);
  }

  async function changeKey() {
    ondisconnect();
  }

  onMount(() => {
    (async () => {
      await prune();
      await poll();
      loaded = true;
      startPolling();
    })();
    return () => stopPolling();
  });
</script>

<div class="wrap">
  <header class="topbar">
    <div class="wordmark">glm<span>-</span>dash</div>
    <div class="topbar-right">
      {#if stats}
        <span class="keychip" title={apikey}>
          <span
            class="dot"
            class:dot-ok={!offline}
            class:dot-bad={offline}
            aria-hidden="true"></span>
          {stats.name || "api key"}
        </span>
      {/if}
      <label class="poll">
        <select
          class="pollselect"
          value={pollMin}
          onchange={setPollMin}
          aria-label="Interval pembaruan data"
        >
          {#each POLL_OPTIONS as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </label>
      <button class="logout" onclick={changeKey}>Keluar</button>
    </div>
  </header>

  {#if !loaded}
    <div class="skeleton card" aria-busy="true"></div>
  {:else if stats}
    {#if offline}
      <Banner
        variant="warn"
        title="Tidak bisa terhubung ke server"
        body="Menampilkan data terakhir yang tersimpan di perangkat ini. Polling lanjut otomatis."
      />
    {/if}
    {#if stats.is_expired}
      <Banner
        variant="danger"
        title="API key kadaluarsa ({new Date(stats.expiry_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })})"
        body="Permintaan baru akan ditolak (403). Data di bawah adalah snapshot terakhir sebelum key berakhir."
        actionLabel="Ganti API key"
        onaction={changeKey}
      />
    {/if}
    {#if rateLimited}
      <Banner variant="warn" title="Kuota window 5 jam sudah habis" body={rlBody} />
    {/if}
    <WindowCard
      used={rateLimited ? rateLimited.tokensUsed : stats.current_usage.tokens_used_in_current_window}
      limit={rateLimited ? rateLimited.tokensLimit || stats.token_limit_per_5h : stats.token_limit_per_5h}
      windowEnd={rateLimited?.windowEndsAt || stats.current_usage.window_ends_at}
    />
    <StatGrid {stats} />
    <AccumulationChart {samples} limit={stats.token_limit_per_5h} windowStart={stats.current_usage.window_started_at} windowEnd={stats.current_usage.window_ends_at} />
    <HistoryTable {windows} />
    <footer class="foot">glm-dash v{__APP_VERSION__} · Data historis tersimpan lokal di perangkat</footer>
  {:else if rateLimited}
    <Banner variant="warn" title="Kuota window 5 jam sudah habis" body={rlBody} />
    <WindowCard
      used={rateLimited.tokensUsed}
      limit={rateLimited.tokensLimit || 1}
      windowEnd={rateLimited.windowEndsAt}
    />
  {:else if failStreak > 0}
    <Banner
      variant="danger"
      title="Gagal memuat data"
      body="API key tidak dikenal atau server bermasalah. Coba ganti key atau periksa koneksi."
      actionLabel="Ganti API key"
      onaction={changeKey}
    />
  {/if}
</div>

<style>
  .wrap {
    max-width: 680px;
    margin: 0 auto;
    padding: 0 var(--space-4) calc(var(--space-8) + env(safe-area-inset-bottom));
  }
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-4) 0;
    border-bottom: 1px solid var(--color-line);
    margin-bottom: var(--space-5);
  }
  .wordmark {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: var(--text-lg);
    letter-spacing: -0.02em;
  }
  .wordmark span {
    color: var(--color-accent);
  }
  .topbar-right {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-width: 0;
  }
  .keychip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--color-ink-2);
    background: var(--color-paper-2);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-full);
    padding: var(--space-1) var(--space-3);
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: var(--radius-full);
    flex: none;
  }
  .dot-ok {
    background: var(--color-ok);
    box-shadow: 0 0 0 3px var(--color-dot-ok-ring);
  }
  .dot-bad {
    background: var(--color-danger);
    box-shadow: 0 0 0 3px var(--color-dot-bad-ring);
  }
  .poll {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    white-space: nowrap;
  }
  .pollselect {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--color-ink);
    background: var(--color-paper-2);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-md);
    padding: var(--space-1) var(--space-2);
  }
  .logout {
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-ink-2);
    background: transparent;
    border: 1px solid var(--color-line);
    border-radius: var(--radius-md);
    min-height: 30px;
    padding: 0 var(--space-3);
    cursor: pointer;
    transition: background var(--dur-fast) var(--ease-out);
    white-space: nowrap;
  }
  .logout:hover {
    background: var(--color-paper-3);
  }
  .skeleton {
    height: 140px;
  }
  .foot {
    text-align: center;
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    padding-top: var(--space-5);
  }
  @media (max-width: 420px) {
    .keychip {
      display: none;
    }
    .topbar {
      padding: var(--space-4) 0;
      padding-top: max(var(--space-4), env(safe-area-inset-top));
    }
  }
</style>
