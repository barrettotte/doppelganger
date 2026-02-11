<script>
  import { onDestroy } from 'svelte';
  import { get } from '../lib/api.js';
  import { startPolling } from '../lib/polling.js';
  import StatusBadge from './StatusBadge.svelte';

  let health = $state(null);

  const stop = startPolling(async () => {
    try {
      health = await get('/health');
    } catch {
      health = null;
    }
  }, 10000);

  onDestroy(stop);
</script>

<header>
  <a class="title" href="/" onclick={(e) => { e.preventDefault(); location.reload(); }}>Doppelganger</a>
  <div class="status">
    {#if health}
      <StatusBadge status={health.status === 'ok' ? 'ok' : 'degraded'} label={health.status} />
    {:else}
      <StatusBadge status="error" label="offline" />
    {/if}
  </div>
</header>

<style>
  header {
    height: var(--header-height);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
  }

  .title {
    font-size: 1.1em;
    font-weight: 600;
    color: var(--text-primary);
  }

  .title:hover {
    color: var(--text-primary);
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
