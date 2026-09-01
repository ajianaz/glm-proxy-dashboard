<script lang="ts">
  import type { SamplePoint } from "../types";
  import { formatNumber, formatCompact, formatTime } from "../format";

  let {
    samples,
    limit,
    windowStart,
    windowEnd,
  }: { samples: SamplePoint[]; limit: number; windowStart: string; windowEnd: string } = $props();

  const W = 660;
  const H = 240;
  const PAD_L = 50;
  const PAD_R = 20;
  const PAD_T = 20;
  const PAD_B = 40;

  const points = $derived.by(() => {
    if (samples.length === 0) return [];
    const start = new Date(windowStart).getTime();
    const end = new Date(windowEnd).getTime();
    const maxVal = Math.max(limit, ...samples.map((s) => s.tokens_used), 1);
    const minVal = 0;
    return samples.map((s) => {
      const xFrac = (new Date(s.captured_at).getTime() - start) / (end - start);
      const yFrac = (s.tokens_used - minVal) / (maxVal - minVal);
      return {
        x: PAD_L + xFrac * (W - PAD_L - PAD_R),
        y: PAD_T + (1 - yFrac) * (H - PAD_T - PAD_B),
        sample: s,
      };
    });
  });

  const limitY = $derived.by(() => {
    if (points.length === 0) return null;
    const maxVal = Math.max(limit, ...samples.map((s) => s.tokens_used), 1);
    const yFrac = limit / maxVal;
    return PAD_T + (1 - yFrac) * (H - PAD_T - PAD_B);
  });

  const linePath = $derived.by(() => {
    if (points.length === 0) return "";
    return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  });

  const areaPath = $derived.by(() => {
    if (points.length === 0) return "";
    const first = points[0];
    const last = points[points.length - 1];
    const baseline = H - PAD_B;
    return `${linePath} L${last.x.toFixed(1)},${baseline} L${first.x.toFixed(1)},${baseline} Z`;
  });

  // Y axis ticks: quarter marks scaled to the visible max (limit-aware)
  const yTicks = $derived.by(() => {
    if (points.length === 0) return [];
    const maxVal = Math.max(limit, ...samples.map((s) => s.tokens_used), 1);
    return [1, 0.75, 0.5, 0.25, 0].map((f) => {
      const val = maxVal * f;
      const y = PAD_T + (1 - f) * (H - PAD_T - PAD_B);
      return { y, label: formatCompact(Math.round(val)) };
    });
  });

  // X axis ticks: start, middle, current end
  const xTicks: Array<{ x: number; label: string; anchor: "start" | "middle" | "end" }> = $derived.by(() => {
    if (points.length === 0) return [];
    const ticks: Array<{ x: number; label: string; anchor: "start" | "middle" | "end" }> = [
      { x: points[0].x, label: formatTime(points[0].sample.captured_at), anchor: "start" },
    ];
    const mid = points[Math.floor(points.length / 2)];
    const last = points[points.length - 1];
    if (mid !== points[0] && mid !== last) {
      ticks.push({ x: mid.x, label: formatTime(mid.sample.captured_at), anchor: "middle" });
    }
    if (last !== points[0]) {
      ticks.push({ x: last.x, label: formatTime(last.sample.captured_at), anchor: "end" });
    }
    return ticks;
  });
</script>

<div class="card">
  <p class="label">Akumulasi token (window berjalan)</p>
  {#if points.length < 2}
    <p class="empty">
      Mengumpulkan data… grafik terisi otomatis saat aplikasi terbuka dan memantau.
    </p>
  {:else}
    <svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Grafik akumulasi token dalam window berjalan">
      {#each yTicks as t (t.y)}
        <line class="grid" x1={PAD_L} y1={t.y} x2={W - PAD_R} y2={t.y} />
        <text class="axis" x={PAD_L - 6} y={t.y + 4} text-anchor="end">{t.label}</text>
      {/each}
      {#each xTicks as t (t.x)}
        <text class="axis" x={t.x} y={H - PAD_B + 20} text-anchor={t.anchor}>{t.label}</text>
      {/each}
      {#if limitY !== null}
        <line class="limit-line" x1={PAD_L} y1={limitY} x2={W - PAD_R} y2={limitY} />
        <text class="limit-text" x={W - PAD_R - 4} y={limitY + 14} text-anchor="end">
          limit {formatNumber(limit)}
        </text>
      {/if}
      <path class="area" d={areaPath} />
      <path class="curve" d={linePath} />
      <circle class="dot" cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="4" />
    </svg>
    <div class="legend">
      <span class="l-fill"><i></i>token terpakai</span>
      <span class="l-limit"><i></i>limit window</span>
    </div>
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
  .chart {
    width: 100%;
    height: auto;
    display: block;
  }
  .grid {
    stroke: var(--color-line);
    stroke-width: 1;
  }
  .axis {
    fill: var(--color-ink-3);
    font-family: var(--font-mono);
    font-size: 11.5px;
  }
  .limit-line {
    stroke: var(--color-ink-3);
    stroke-width: 1.5;
    stroke-dasharray: 5 4;
  }
  .limit-text {
    fill: var(--color-ink-2);
    font-family: var(--font-mono);
    font-size: 11.5px;
  }
  .area {
    fill: var(--color-accent-area);
  }
  .curve {
    fill: none;
    stroke: var(--color-accent);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .dot {
    fill: var(--color-accent);
  }
  .legend {
    display: flex;
    gap: var(--space-4);
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    margin-top: var(--space-3);
    flex-wrap: wrap;
  }
  .legend i {
    display: inline-block;
    width: 12px;
    height: 3px;
    border-radius: 2px;
    vertical-align: middle;
    margin-right: 6px;
  }
  .l-fill i {
    background: var(--color-accent);
  }
  .l-limit i {
    background: repeating-linear-gradient(90deg, var(--color-ink-3) 0 4px, transparent 4px 8px);
  }
</style>
