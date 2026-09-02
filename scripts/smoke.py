"""UI smoke test: onboarding -> dashboard with mocked /stats, desktop + mobile.

- Blocks the PWA service worker (deterministic routing to page.route mocks).
- Seeds IndexedDB with 12 realistic samples so the accumulation chart has data
  (in real use the 60s poll interval builds this over hours).
- Covers 429 UX: mid-session quota banner (snapshot kept) and cold-429
  onboarding message, plus logout returning to onboarding.
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
    """Build one mocked /stats 200 body; usage grows with each poll."""
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


def mock_429_body():
    """Build the proxy's real 429 error shape for the rate-limited flows."""
    return {
        "error": {
            "message": "Token limit exceeded for current 5-hour window",
            "type": "rate_limit_exceeded",
            "tokens_used": 16_427_618,
            "tokens_limit": 15_000_000,
            "window_ends_at": WINDOW_END,
        }
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
    """Run the full smoke suite: happy path, 429 flows, logout, mobile QA."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        errors = []

        # Single shared route: tests are sequential, so a module-level status
        # flag keeps the mock deterministic (no unroute/route races).
        stats_status = {"code": 200}

        CORS_HEADERS = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, x-api-key, Content-Type",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
        }

        async def handle_stats_route(route):
            # The app's fetch sends Authorization/x-api-key -> non-simple request
            # -> the browser sends an OPTIONS preflight that ALSO matches this
            # route. Fulfill it with CORS headers or the real request never fires
            # (fetch throws instantly, looks like a network error).
            try:
                if route.request.method == "OPTIONS":
                    await route.fulfill(status=204, headers=CORS_HEADERS)
                    return
                body = mock_stats() if stats_status["code"] == 200 else mock_429_body()
                await route.fulfill(
                    status=stats_status["code"],
                    content_type="application/json",
                    headers=CORS_HEADERS,
                    body=json.dumps(body),
                )
            except Exception as exc:  # surface handler bugs instead of silent aborts
                print(f"ROUTE HANDLER ERROR: {exc!r}")
                try:
                    await route.abort()
                except Exception:
                    pass

        async def new_page(viewport):
            # service_workers="block": the PWA SW (clientsClaim) would otherwise
            # route /stats through its NetworkFirst handler, bypassing page.route
            # and hitting the real server. Deterministic tests block it.
            ctx = await browser.new_context(viewport=viewport, service_workers="block")
            page = await ctx.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

            def _on_console(m):
                if m.type != "error":
                    return
                # Expected: the browser logs every non-2xx mock response as a
                # resource error. Only 429 flows are mocked non-2xx in this test.
                if "status of 429" in m.text:
                    return
                errors.append(f"console.error: {m.text}")

            page.on("console", _on_console)
            await page.route("**/stats", handle_stats_route)
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

        # --- mid-session 429: dashboard loaded, then window quota exhausts ---
        # connect with 200, flip the route to 429, set poll to 1 minute and
        # wait for the quota banner. Dashboard must stay calm: banner + last
        # snapshot, no scary "key tidak dikenal" message.
        ctx3, page3 = await new_page({"width": 1280, "height": 900})
        await page3.goto(BASE, wait_until="networkidle")
        await page3.wait_for_selector("#keyinput")
        await page3.fill("#keyinput", "sk-tes...1234")
        await page3.wait_for_function(
            "() => { const b = document.querySelector('button[type=submit]'); return b && !b.disabled; }",
            timeout=5000,
        )
        await page3.click("button[type=submit]")
        try:
            await page3.wait_for_selector(".card .num", timeout=8000)
        except Exception:
            body = await page3.inner_text("body")
            print("CTX3 TIMEOUT BODY:", body[:600])
            await page3.screenshot(path=str(ROOT / "qa-debug-ctx3.png"))
            raise

        stats_status["code"] = 429
        await page3.select_option(".pollselect", "1")
        await page3.wait_for_selector(".banner", timeout=75_000)
        banner_txt = await page3.inner_text(".banner")
        assert "Kuota window 5 jam" in banner_txt, f"429 banner wrong: {banner_txt}"
        # snapshot must still be rendered (calm mode, not an error wipe)
        num = await page3.inner_text(".card .num")
        assert num.strip(), "window card vanished during 429"
        print(f"mid-session 429: banner shown, snapshot kept (num={num})")
        await page3.screenshot(path=str(ROOT / "qa-429-desktop.png"), full_page=True)

        # --- logout from the same session ---
        await page3.click("button.logout")
        await page3.wait_for_selector("#keyinput", timeout=8000)
        print("logout returns to onboarding")

        # --- cold 429 on onboarding: quota message, not generic server error ---
        ctx4, page4 = await new_page({"width": 375, "height": 812})
        await page4.goto(BASE, wait_until="networkidle")
        await page4.wait_for_selector("#keyinput")
        await page4.fill("#keyinput", "sk-tes...1234")
        await page4.wait_for_function(
            "() => { const b = document.querySelector('button[type=submit]'); return b && !b.disabled; }",
            timeout=5000,
        )
        await page4.click("button[type=submit]")
        await page4.wait_for_selector(".error", timeout=8000)
        err_txt = await page4.inner_text(".error")
        assert "Kuota window 5 jam" in err_txt, f"onboarding 429 message wrong: {err_txt}"
        print("onboarding 429 shows quota message")
        await page4.screenshot(path=str(ROOT / "qa-429-mobile.png"), full_page=True)

        await ctx.close()
        await ctx2.close()
        await ctx3.close()
        await ctx4.close()
        await browser.close()

        if errors:
            print("JS ERRORS:")
            for e in errors:
                print(" ", e)
            raise SystemExit(1)
        print("SMOKE TEST PASS (no JS errors)")


asyncio.run(main())
