<script lang="ts">
  import { formatNumber, formatPercent, formatTime, countdown } from "../format";

  let { used, limit, windowEnd }: { used: number; limit: number; windowEnd: string } = $props();

  const pct = $derived(limit > 0 ? (used / limit) * 100 : 0);
</script>

<div class="card">
  <p class="label">Kuota window 5 jam</p>
  <div>
    <span class="num">{formatNumber(used)}</span>
    <span class="denom"> / {formatNumber(limit)} token</span>
  </div>
  <div
    class="bar"
    role="progressbar"
    aria-valuenow={Math.round(pct)}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label="Persen limit terpakai"
  >
    <div class="fill" style:width="{Math.min(100, pct)}%"></div>
  </div>
  <div class="meta">
    <span>{formatPercent(used, limit)} terpakai</span>
    <span class="mono">
      Reset {formatTime(windowEnd)} ({countdown(windowEnd)})
    </span>
  </div>
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
  .num {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .denom {
    font-size: var(--text-sm);
    color: var(--color-ink-3);
  }
  .bar {
    height: 8px;
    background: var(--color-paper-3);
    border-radius: var(--radius-full);
    margin: var(--space-4) 0 var(--space-2);
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: var(--color-accent);
    border-radius: var(--radius-full);
    transition: width var(--dur-base) var(--ease-out);
  }
  .meta {
    display: flex;
    justify-content: space-between;
    gap: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-ink-2);
    flex-wrap: wrap;
  }
  .mono {
    font-family: var(--font-mono);
  }
</style>
