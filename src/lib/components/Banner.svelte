<script lang="ts">
  import WarningIcon from "./icons/WarningIcon.svelte";

  let {
    variant = "warn",
    title,
    body,
    actionLabel,
    onaction,
  }: {
    variant?: "warn" | "danger";
    title: string;
    body: string;
    actionLabel?: string;
    onaction?: () => void;
  } = $props();
</script>

<div class="banner {variant}" role="alert">
  <WarningIcon />
  <div class="body">
    <strong>{title}</strong>
    {body}
  </div>
  {#if actionLabel && onaction}
    <button class="action" onclick={onaction}>{actionLabel}</button>
  {/if}
</div>

<style>
  .banner {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    flex-wrap: wrap;
    border-radius: var(--radius-md);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
    font-size: var(--text-sm);
  }
  .warn {
    background: var(--color-paper-3);
    border: 1px solid var(--color-line);
    color: var(--color-ink-2);
  }
  .danger {
    background: var(--color-danger-soft);
    border: 1px solid var(--color-danger-border);
    color: var(--color-danger);
  }
  .body {
    flex: 1;
    min-width: 200px;
  }
  .body strong {
    display: block;
    margin-bottom: 2px;
  }
  .action {
    background: transparent;
    color: inherit;
    border: 1px solid currentColor;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 600;
    min-height: 38px;
    padding: var(--space-2) var(--space-4);
    cursor: pointer;
    align-self: center;
    transition: background var(--dur-fast) var(--ease-out);
  }
  .action:hover {
    background: var(--color-danger-border);
  }
</style>
