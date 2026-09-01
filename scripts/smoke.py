"""UI smoke test: onboarding -> dashboard with mocked /stats, desktop + mobile.

- Blocks the PWA service worker (deterministic routing to page.route mocks).
- Seeds IndexedDB with 12 realistic samples so the accumulation chart has data
  (in real use the 60s poll interval builds this over hours).
Run: python3 scripts/smoke.py   (requires `bun run preview` on :4173)
"""
import asyncio
import glob
import json
import pathlib
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROMIUM = glob.glob("/opt/data/.cloakbrowser/chromium-*/chrome")[0]
BASE = "http://localhost:4173"

POLL_COUNT = {"n": 0}

# Fixed 5h window for the whole test run (window_start only rolls every 5h)
_NOW = datetime.now(timezone.utc)
WINDOW_START = (_NOW - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
WINDOW_END = (_NOW + timedelta(hours=3)).isoformat().replace("+00:00", "Z")


def mock_stats():
    POLL_COUNT["n"] += 1
    n = POLL_COUNT["n"]
    used = 4_000_000 + n * 50_000
    return {
        "key": "sk-mock",
        "name": "klien-demo",
        "model": "glm-4.7",
        "token_limit_per_5h": 15_000_000,
        "expiry_date": "2099-12-31T23:59:59Z",
        "created_at": "2026-08-01T00:00:00Z",
        "last_used": "2026-09-01T17:46:00Z",
        "is_expired": False,
        "current_usage": {
            "tokens_used_in_current_window": used,
            "window_started_at": WINDOW_START,
            "window_ends_at": WINDOW_END,
            "remaining_tokens": 15_000_000 - used,
        },
        "total_requests": 1240 + n,
        "total_lifetime_tokens": 18_392_104,
    }


SEED_JS_BODY = """
async (args) => {
  const [wsIso, weIso] = args;
  const req = indexedDB.open('glm-dash', 1);
  req.onupgradeneeded = () => {
    const d = req.result;
    if (!d.objectStoreNames.contains('windows')) {
      const s = d.createObjectStore('windows', { keyPath: 'key' });
      s.createIndex('by-window-start', 'window_start');
    }
    if (!d.objectStoreNames.contains('samples')) {
      const s = d.createObjectStore('samples', { keyPath: 'key' });
      s.createIndex('by-captured-at', 'captured_at');
    }
  };
  const db = await new Promise((res, rej) => { req.onsuccess = () => res(req.result); req.onerror = () => rej(req.error); });
  const count = await new Promise((res) => {
    const rq = db.transaction('samples', 'readonly').objectStore('samples').count();
    rq.onsuccess = () => res(rq.result);
  });
  if (count >= 12) return 'already-seeded';
  const tx = db.transaction(['samples', 'windows'], 'readwrite');
  const st = tx.objectStore('samples');
  const wt = tx.objectStore('windows');
  const wsT = new Date(wsIso).getTime();
  for (let i = 1; i <= 12; i++) {
    const cap = new Date(wsT + i * 10 * 60 * 1000).toISOString();
    st.put({ key: wsIso + '|' + cap, window_start: wsIso, window_end: weIso,
             tokens_used: 2000000 + i * 180000, requests: 300 + i, captured_at: cap });
  }
  wt.put({ key: wsIso, window_start: wsIso, window_end: weIso,
           tokens_used: 4160000, requests: 312, captured_at: new Date().toISOString() });
  await new Promise((res) => { tx.oncomplete = res; });
  return 'seeded-12';
}
"""


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        errors = []

        def make_route():
            async def handle_route(route):
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(mock_stats()),
                )
            return handle_route

        async def new_page(viewport):
            # service_workers="block": the PWA SW (clientsClaim) would otherwise
            # route /stats through its NetworkFirst handler, bypassing page.route
            # and hitting the real server. Deterministic tests block it.
            ctx = await browser.new_context(viewport=viewport, service_workers="block")
            page = await ctx.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on(
                "console",
                lambda m: errors.append(f"console.error: {m.text}")
                if m.type == "error"
                else None,
            )
            await page.route("**/stats", make_route())
            return ctx, page

        async def seed_history(page):
            # Deterministic seeding AFTER load, BEFORE submit (init-script races the app)
            await page.evaluate(SEED_JS_BODY, [WINDOW_START, WINDOW_END])

        # --- desktop flow: onboarding -> dashboard ---
        ctx, page = await new_page({"width": 1280, "height": 900})
        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_selector("#keyinput")
        await page.fill("#keyinput", "sk-test-mock-key-1234")
        # wait until Svelte bind:value picked up the input (button becomes enabled)
        await page.wait_for_function(
            "() => { const b = document.querySelector('button[type=submit]'); return b && !b.disabled; }",
            timeout=5000,
        )
        await page.click("button[type=submit]")
        try:
            await page.wait_for_selector(".card .num", timeout=8000)
        except Exception:
            body = await page.inner_text("body")
            print("DESKTOP TIMEOUT BODY:", body[:600])
            await page.screenshot(path=str(ROOT / "qa-debug-desktop.png"))
            raise
        hero = await page.inner_text(".card .num")
        expected = f"{4_000_000 + POLL_COUNT['n'] * 50_000:,}".replace(",", ".")
        assert hero == expected, f"hero number wrong: got {hero}, expected {expected}"
        print(f"dashboard rendered, hero={hero}")

        # Seed AFTER submit: connect() wipes local data on fresh key (by design),
        # so seeding earlier would be destroyed. Seed now, then reload to re-read.
        seed_result = await seed_history(page)
        print(f"seed: {seed_result}")
        await page.reload(wait_until="networkidle")
        await page.wait_for_selector(".card .num", timeout=8000)

        # chart: 12 seeded samples + live polls -> real curve
        await page.wait_for_selector("svg.chart path.curve", timeout=8000)
        pts = await page.evaluate(
            "() => document.querySelector('svg.chart path.curve').getAttribute('d').split('L').length"
        )
        assert pts >= 5, f"curve should have several points, got {pts}"
        print(f"chart curve rendered with {pts} points")

        # history table shows the seeded window
        hist_rows = await page.locator(".card table tbody tr").count()
        assert hist_rows >= 1, "history table empty"
        print(f"history rows: {hist_rows}")

        await page.screenshot(path=str(ROOT / "qa-desktop.png"), full_page=True)

        # reload already tested above (dashboard restored + chart visible)

        # --- mobile flow (fresh context, own storage) ---
        ctx2, page2 = await new_page({"width": 375, "height": 812})
        await page2.goto(BASE, wait_until="networkidle")
        await page2.wait_for_selector("#keyinput")
        await page2.fill("#keyinput", "sk-test-mock-key-1234")
        await page2.wait_for_function(
            "() => { const b = document.querySelector('button[type=submit]'); return b && !b.disabled; }",
            timeout=5000,
        )
        await page2.click("button[type=submit]")
        await page2.wait_for_selector(".card .num", timeout=8000)
        overflow = await page2.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        print(f"mobile overflow: {overflow}px")
        assert overflow == 0, "horizontal overflow on mobile"
        await page2.screenshot(path=str(ROOT / "qa-mobile.png"), full_page=True)

        await ctx.close()
        await ctx2.close()
        await browser.close()

        if errors:
            print("JS ERRORS:")
            for e in errors:
                print(" ", e)
            raise SystemExit(1)
        print("SMOKE TEST PASS (no JS errors)")


asyncio.run(main())
