<script lang="ts">
  import { onMount } from "svelte";
  import { getApiKey, setApiKey, clearApiKey, fetchStats } from "./lib/api";
  import { clearAll } from "./lib/db";
  import Dashboard from "./lib/components/Dashboard.svelte";
  import Onboarding from "./lib/components/Onboarding.svelte";

  type AppState =
    | { screen: "loading" }
    | { screen: "onboarding" }
    | { screen: "dashboard"; apiKey: string };

  let state: AppState = $state({ screen: "loading" });

  async function connect(key: string) {
    const res = await fetchStats(key);
    if (!res.ok) {
      // Let Onboarding surface the error; it owns the input state.
      throw res.error;
    }
    // Fresh key: wipe stale local data from a previous key.
    await clearAll();
    setApiKey(key);
    state = { screen: "dashboard", apiKey: key };
  }

  function disconnect() {
    clearApiKey();
    clearAll();
    state = { screen: "onboarding" };
  }

  onMount(() => {
    const key = getApiKey();
    state = key ? { screen: "dashboard", apiKey: key } : { screen: "onboarding" };
  });
</script>

{#if state.screen === "loading"}
  <div class="boot" aria-busy="true"></div>
{:else if state.screen === "onboarding"}
  <Onboarding onconnect={connect} />
{:else if state.screen === "dashboard"}
  <Dashboard apikey={state.apiKey} ondisconnect={disconnect} />
{/if}

<style>
  .boot {
    min-height: 100dvh;
    display: flex;
  }
</style>
