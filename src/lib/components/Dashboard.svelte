<script lang="ts">
  import { onMount } from "svelte";
  import { fetchStats } from "../api";
  import { recordPoll, getWindows, getSamples, prune, clearAll } from "../db";
  import type { HistoryPoint, SamplePoint, StatsResponse } from "../types";
  import WindowCard from "./WindowCard.svelte";
  import StatGrid from "./StatGrid.svelte";
  import AccumulationChart from "./AccumulationChart.svelte";
  import HistoryTable from "./HistoryTable.svelte";
  import Banner from "./Banner.svelte";

  let { apikey, ondisconnect }: { apikey: string; ondisconnect: () => void } = $props();

  const POLL_MS = 60_000;

  let stats = $state<StatsResponse | null>(null);
  let windows = $state<HistoryPoint[]>([]);
  let samples = $state<SamplePoint[]>([]);
  let lastSync = $state<Date | null>(null);
  let failStreak = $state(0);
  let offline = $state(false);
  let loaded = $state(false);
  let timer: ReturnType<typeof setInterval> | undefined;
  let seq = 0;

  async function poll() {
    const reqId = ++seq;
    const res = await fetchStats(apikey);
    if (reqId !== seq) return; // stale response guard
    if (res.ok) {
      stats = res.data;
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
      // Network errors (kind === "network") flip the offline indicator;
      // auth errors surface via the banner below.
      offline = res.error.kind === "network";
      if (res.error.kind === "forbidden") {
        // expired: stop polling, keep snapshot
        stopPolling();
      }
    }
  }

  function stopPolling() {
    if (timer) clearInterval(timer);
    timer = undefined;
  }

  async function changeKey() {
    ondisconnect();
  }

  onMount(() => {
    (async () => {
      await prune();
      await poll();
      loaded = true;
      timer = setInterval(poll, POLL_MS);
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
      {#if lastSync}
        <span class="sync">Tersinkron {lastSync.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}</span>
      {/if}
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
    <WindowCard {stats} />
    <StatGrid {stats} />
    <AccumulationChart {samples} limit={stats.token_limit_per_5h} windowStart={stats.current_usage.window_started_at} windowEnd={stats.current_usage.window_ends_at} />
    <HistoryTable {windows} />
    <footer class="foot">glm-dash v{__APP_VERSION__} · Data historis tersimpan lokal di perangkat</footer>
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
  .sync {
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    white-space: nowrap;
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
    .sync {
      display: none;
    }
    .topbar {
      padding: var(--space-4) 0;
      padding-top: max(var(--space-4), env(safe-area-inset-top));
    }
  }
</style>
