const idFmt = new Intl.NumberFormat("id-ID");
const dateTimeFmt = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
});
const dayFmt = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
});
const fullDayFmt = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatNumber(n: number): string {
  return idFmt.format(n);
}

export function formatPercent(part: number, total: number): string {
  if (total <= 0) return "0%";
  const pct = Math.min(100, (part / total) * 100);
  // one decimal only when it matters (below 10%)
  const v = pct < 10 ? Math.round(pct * 10) / 10 : Math.round(pct);
  return `${idFmt.format(v).replace(",", ",")}%`.replace(".", ",");
}

export function formatTime(iso: string): string {
  return dateTimeFmt.format(new Date(iso));
}

export function formatDay(iso: string): string {
  return dayFmt.format(new Date(iso));
}

/** "31 Agu 2026" full date for expiry display. */
export function formatDate(iso: string): string {
  return fullDayFmt.format(new Date(iso));
}

/** "2 j 14 m lagi" style countdown until ISO timestamp. */
export function countdown(iso: string, now = new Date()): string {
  const diff = new Date(iso).getTime() - now.getTime();
  if (diff <= 0) return "segera";
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  if (hours >= 24) {
    const d = Math.floor(hours / 24);
    return `${d} h ${hours % 24} j lagi`;
  }
  if (hours > 0) return `${hours} j ${mins % 60} m lagi`;
  return `${mins} m lagi`;
}

/** "12 mnt lalu" style relative time from ISO timestamp. */
export function timeAgo(iso: string, now = new Date()): string {
  const diff = now.getTime() - new Date(iso).getTime();
  if (diff < 0) return "baru saja";
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "baru saja";
  if (mins < 60) return `${mins} mnt lalu`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} jam lalu`;
  const days = Math.floor(hours / 24);
  return `${days} hari lalu`;
}

/** Masked key display: show name + last 4 chars. */
export function maskKey(key: string): string {
  if (key.length <= 8) return key;
  return `${key.slice(0, 3)}…${key.slice(-4)}`;
}

/** Compact chart-axis label: 15000000 -> "15 jt", 850000 -> "850 rb". */
export function formatCompact(n: number): string {
  if (n >= 1_000_000_000) return `${trim(n / 1_000_000_000)} m`;
  if (n >= 1_000_000) return `${trim(n / 1_000_000)} jt`;
  if (n >= 1_000) return `${trim(n / 1_000)} rb`;
  return idFmt.format(n);
}

function trim(v: number): string {
  return idFmt.format(Math.round(v * 10) / 10);
}
