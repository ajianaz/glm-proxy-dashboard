<script lang="ts">
  import type { StatsResponse } from "../types";
  import { formatNumber, timeAgo } from "../format";

  let { stats }: { stats: StatsResponse } = $props();
</script>

<div class="grid">
  <div class="stat">
    <div class="label">Permintaan total</div>
    <div class="value">{formatNumber(stats.total_requests)}</div>
  </div>
  <div class="stat">
    <div class="label">Token seumur hidup</div>
    <div class="value">{formatNumber(stats.total_lifetime_tokens)}</div>
  </div>
  <div class="stat">
    <div class="label">Model</div>
    <div><span class="chip">{stats.model}</span></div>
  </div>
  <div class="stat">
    <div class="label">Terakhir dipakai</div>
    <div class="value value-sm">{timeAgo(stats.last_used)}</div>
  </div>
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }
  .stat {
    background: var(--color-paper-2);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
  }
  .label {
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    margin-bottom: var(--space-1);
  }
  .value {
    font-family: var(--font-mono);
    font-size: var(--text-lg);
    font-weight: 650;
    letter-spacing: -0.01em;
  }
  .value-sm {
    font-size: var(--text-base);
    padding-top: 2px;
  }
  .chip {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
    background: var(--color-accent-soft);
    color: var(--color-accent);
    border-radius: var(--radius-full);
    padding: 0.1rem var(--space-3);
  }
</style>
