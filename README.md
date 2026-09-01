# glm-proxy-dashboard

PWA dashboard untuk memantau pemakaian API key [glm.ajianaz.dev](https://glm.ajianaz.dev) (glm-proxy-golang).

Masukkan API key sekali → dashboard menampilkan window rate limit 5 jam, statistik total, grafik akumulasi token, dan riwayat window. Riwayat tersimpan lokal di browser (IndexedDB), API key tersimpan di localStorage — tidak ada data yang dikirim ke pihak lain.

## Fitur

- **Window 5 jam berjalan** — token terpakai, progress bar, countdown reset
- **Grafik akumulasi** — dibangun dari poll `/stats` tiap 60 detik saat app terbuka
- **Riwayat window** — tersimpan lokal (IndexedDB), pruned otomatis (>30 hari)
- **PWA** — installable, offline shell, indikator offline
- **Dark mode** — mengikuti `prefers-color-scheme`
- **Key states** — 401 (invalid) / 403 (expired) ditangani dengan banner + snapshot terakhir

## Stack

- Svelte 5 (runes) + Vite, tanpa framework routing (1 halaman)
- `vite-plugin-pwa` (Workbox), `idb` untuk IndexedDB
- Chart: SVG inline hand-rolled (tanpa dependency chart library)
- Total bundle: ~25 KB gzipped

## Development

```bash
bun install
bun run dev        # dev server
bun run build      # production build ke dist/
bun run preview    # serve dist/ di :4173
bun run check      # svelte-check
```

Smoke test (butuh `bun run preview` jalan + Python Playwright):

```bash
bun run preview &
python3 scripts/smoke.py
```

## Deployment

Static build di-serve oleh Caddy dalam container:

```bash
docker compose up -d
```

Label Traefik contoh ada di `docker-compose.yml` (domain `glm-dash.ajianaz.dev`). Endpoint API bisa dioverride via `VITE_API_BASE` saat build (default `https://glm.ajianaz.dev`).

## Terkait

- [glm-proxy-golang](https://github.com/ajianaz/glm-proxy-golang) — proxy server yang menyediakan endpoint `/stats` dan `/v1/*`
