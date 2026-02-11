<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { formatUptime } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
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

  let status: any = $state(null);
  let health: any = $state(null);
  let config: ConfigData | null = $state(null);
  let loading = $state(true);

  // Fetch bot status, system health, and full config in parallel.
  async function loadData() {
    try {
      const [s, h, c] = await Promise.all([
        get('/api/status'),
        get('/health'),
        get('/api/config'),
      ]);
      status = s;
      health = h;
      config = c;

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
    <div class="section">
      <h3>Bot Status</h3>
      <div class="info-card">
        <div class="info-row">
          <span class="info-label">Connection</span>
          <StatusBadge status={status?.connected ? 'connected' : 'disconnected'} label={status?.connected ? 'Connected' : 'Disconnected'} />
        </div>
        {#if status?.connected}
          <div class="info-row">
            <span class="info-label">Username</span>
            <span>{status.username}</span>
          </div>
          {#if status.guilds?.length}
            <div class="info-row">
              <span class="info-label">Guild</span>
              <span title={status.guilds[0].id}>{status.guilds[0].name} ({status.guilds[0].member_count} members)</span>
            </div>
          {/if}
          <div class="info-row">
            <span class="info-label">Uptime</span>
            <span>{formatUptime(status.uptime_seconds)}</span>
          </div>
        {/if}
      </div>
    </div>

    <div class="section">
      <h3>System Health</h3>
      <div class="info-card">
        {#if health}
          <div class="info-row">
            <span class="info-label">Status</span>
            <StatusBadge status={health.status === 'healthy' ? 'ok' : 'degraded'} label={health.status} />
          </div>
          <div class="info-row">
            <span class="info-label">Database</span>
            <StatusBadge status={health.database === 'connected' ? 'connected' : 'error'} label={health.database} />
          </div>
          <div class="info-row">
            <span class="info-label">TTS Model</span>
            <span>{health.tts_model}</span>
          </div>
          <div class="info-row">
            <span class="info-label">GPU Available</span>
            <span>{health.gpu_available ? 'Yes' : 'No'}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Voices Loaded</span>
            <span>{health.voices_loaded}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Cache Size</span>
            <span>{health.cache_size}</span>
          </div>
        {:else}
          <p class="muted">Health data unavailable.</p>
        {/if}
      </div>
    </div>

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
