<script lang="ts">
  import type { StatsError } from "../api";

  let { onconnect }: { onconnect: (key: string) => Promise<void> } = $props();

  let apiKey = $state("");
  let busy = $state(false);
  let error = $state<string | null>(null);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    const key = apiKey.trim();
    if (!key || busy) return;
    busy = true;
    error = null;
    try {
      await onconnect(key);
    } catch (err) {
      error = describe(err as StatsError);
    } finally {
      busy = false;
    }
  }

  function describe(err: StatsError): string {
    switch (err.kind) {
      case "unauthorized":
        return "API key tidak dikenal. Periksa kembali key kamu.";
      case "forbidden":
        return "API key sudah kadaluarsa. Minta key baru ke admin.";
      case "network":
        return "Tidak bisa terhubung ke server. Periksa koneksi internet kamu.";
      default:
        return `Server merespons dengan error (HTTP ${err.status}).`;
    }
  }
</script>

<div class="onboard">
  <form class="card" onsubmit={submit}>
    <div class="logo" aria-hidden="true">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <path
          d="M3 14 L7 8 L11 12 L15 5 L19 10"
          stroke="var(--color-accent-ink)"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </div>
    <h1 class="title">glm-dash</h1>
    <p class="sub">Pantau pemakaian API key GLM kamu: token, permintaan, dan window rate limit.</p>

    <label class="field-label" for="keyinput">API key</label>
    <input
      class="input"
      id="keyinput"
      type="password"
      placeholder="sk-…"
      autocomplete="off"
      spellcheck="false"
      bind:value={apiKey}
    />
    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <button class="btn" type="submit" disabled={busy || apiKey.trim().length === 0}>
      {busy ? "Menyambungkan…" : "Sambungkan"}
    </button>

    <p class="privacy">
      Key hanya tersimpan di perangkat ini (localStorage) dan hanya dikirim ke
      glm.ajianaz.dev.
    </p>
  </form>
</div>

<style>
  .onboard {
    min-height: 100dvh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-4);
    padding-top: max(var(--space-4), env(safe-area-inset-top));
  }
  .card {
    width: 100%;
    max-width: 400px;
  }
  .logo {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    background: var(--color-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--space-4);
  }
  .title {
    font-family: var(--font-mono);
    font-size: var(--text-xl);
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0 0 var(--space-1);
  }
  .sub {
    color: var(--color-ink-2);
    font-size: var(--text-sm);
    margin: 0 0 var(--space-5);
  }
  .field-label {
    display: block;
    font-size: var(--text-sm);
    font-weight: 600;
    margin-bottom: var(--space-2);
  }
  .input {
    width: 100%;
    font-family: var(--font-mono);
    font-size: 1rem; /* 16px: prevents iOS focus zoom */
    background: var(--color-paper-2);
    color: var(--color-ink);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-4);
    min-height: 48px;
    transition:
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }
  .input:focus {
    outline: none;
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px var(--color-accent-soft);
  }
  .input::placeholder {
    color: var(--color-ink-3);
  }
  .error {
    color: var(--color-danger);
    font-size: var(--text-sm);
    margin: var(--space-2) 0 0;
  }
  .btn {
    width: 100%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: var(--text-sm);
    font-weight: 600;
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    min-height: 44px;
    padding: var(--space-3) var(--space-5);
    margin-top: var(--space-3);
    background: var(--color-accent);
    color: var(--color-accent-ink);
    transition:
      background var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }
  .btn:hover:not(:disabled) {
    background: var(--color-accent-hover);
  }
  .btn:active:not(:disabled) {
    transform: translateY(1px);
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .privacy {
    display: flex;
    gap: var(--space-2);
    align-items: flex-start;
    font-size: var(--text-xs);
    color: var(--color-ink-3);
    background: var(--color-paper-3);
    border-radius: var(--radius-md);
    padding: var(--space-3);
    margin-top: var(--space-4);
  }
</style>
