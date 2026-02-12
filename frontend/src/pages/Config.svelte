<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from '../lib/api';
  import { toasts } from '../lib/toast';
  import Spinner from '../components/Spinner.svelte';

  interface ConfigEntry {
    key: string;
    value: string;
  }

  interface ConfigSection {
    name: string;
    entries: ConfigEntry[];
  }

  interface ConfigData {
    sections: ConfigSection[];
  }

  let config: ConfigData | null = $state(null);
  let loading = $state(true);

  // Fetch the full config.
  async function loadData() {
    try {
      config = await get('/api/config');
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      loading = false;
    }
  }

  // Format a snake_case key into a readable label.
  function formatKey(key: string): string {
    return key.replace(/_/g, ' ');
  }

  // Check if a value is a redacted secret.
  function isRedacted(value: string): boolean {
    return value === '********';
  }

  onMount(loadData);
</script>

<div class="config-page">
  <h2>Config</h2>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else}
    {#if config}
      {#each config.sections as section}
        <div class="section">
          <h3>{section.name}</h3>
          <div class="info-card">
            {#each section.entries as entry}
              <div class="info-row">
                <span class="info-label">{formatKey(entry.key)}</span>
                {#if isRedacted(entry.value)}
                  <code class="redacted">{entry.value}</code>
                {:else}
                  <code>{entry.value || '(empty)'}</code>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/each}
    {/if}
  {/if}
</div>

<style lang="scss">
  .config-page {
    max-width: 700px;
  }

  .info-label {
    min-width: 160px;
    text-transform: capitalize;
  }

  .redacted {
    opacity: 0.5;
    font-style: italic;
  }
</style>
