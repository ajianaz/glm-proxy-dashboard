<script lang="ts">
  import type { HistoryPoint } from "../types";
  import { formatNumber, formatCompact } from "../format";

  let { windows }: { windows: HistoryPoint[] } = $props();

  function range(p: HistoryPoint): string {
    const f = (iso: string) =>
      new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
    return `${f(p.window_start)}-${f(p.window_end)}`;
  }
</script>

<div class="card">
  <p class="label">Riwayat window</p>
  {#if windows.length === 0}
    <p class="empty">Belum ada riwayat. Data terkumpul saat aplikasi terbuka.</p>
  {:else}
    <table>
      <thead>
        <tr><th>Window</th><th class="num">Token</th><th class="num">Req</th></tr>
      </thead>
      <tbody>
        {#each windows as w (w.key)}
          <tr>
            <td class="mono">{range(w)}</td>
            <td class="num" title={formatNumber(w.tokens_used)}>{formatCompact(w.tokens_used)}</td>
            <td class="num">{formatNumber(w.requests)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

<style>
  .card {
    background: var(--color-paper-2);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    margin-bottom: var(--space-4);
  }
  .label {
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-ink-3);
    margin: 0 0 var(--space-3);
  }
  .empty {
    color: var(--color-ink-3);
    font-size: var(--text-sm);
    margin: 0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
  }
  th {
    text-align: left;
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--color-ink-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--color-line);
  }
  td {
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--color-line);
  }
  tr:last-child td {
    border-bottom: none;
  }
  th.num,
  td.num {
    text-align: right;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }
  .mono {
    font-family: var(--font-mono);
  }
</style>
