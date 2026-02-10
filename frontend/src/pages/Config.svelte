<script>
  import { onMount } from 'svelte';
  import { get } from '../lib/api.js';
  import { formatUptime } from '../lib/format.js';
  import StatusBadge from '../components/StatusBadge.svelte';
  import Spinner from '../components/Spinner.svelte';

  let status = $state(null);
  let health = $state(null);
  let loading = $state(true);

  // Fetch bot status and system health data in parallel.
  async function loadData() {
    try {
      const [s, h] = await Promise.all([get('/api/status'), get('/health')]);
      status = s;
      health = h;

    } catch (e) {
      console.error('Failed to load config:', e);
    } finally {
      loading = false;
    }
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
          <span class="label">Connection</span>
          <StatusBadge status={status?.connected ? 'connected' : 'disconnected'} label={status?.connected ? 'Connected' : 'Disconnected'} />
        </div>
        {#if status?.connected}
          <div class="info-row">
            <span class="label">Username</span>
            <span>{status.username}</span>
          </div>
          <div class="info-row">
            <span class="label">Guilds</span>
            <span>{status.guild_count}</span>
          </div>
          {#each status.guilds as guild}
            <div class="info-row indent">
              <span class="label">Guild</span>
              <span>{guild.name} ({guild.member_count} members)</span>
            </div>
          {/each}
          <div class="info-row">
            <span class="label">Uptime</span>
            <span>{formatUptime(status.uptime_seconds)}</span>
          </div>
        {/if}
      </div>
    </div>

    <div class="section">
      <h3>Bot Configuration</h3>
      <div class="info-card">
        {#if status?.config}
          {#each Object.entries(status.config) as [key, value]}
            <div class="info-row">
              <span class="label">{key.replace(/_/g, ' ')}</span>
              <code>{value}</code>
            </div>
          {/each}
        {:else}
          <p class="muted">No config available (bot not connected).</p>
        {/if}
      </div>
    </div>

    <div class="section">
      <h3>System Health</h3>
      <div class="info-card">
        {#if health}
          <div class="info-row">
            <span class="label">Status</span>
            <StatusBadge status={health.status === 'ok' ? 'ok' : 'degraded'} label={health.status} />
          </div>
          <div class="info-row">
            <span class="label">Database</span>
            <StatusBadge status={health.database === 'connected' ? 'connected' : 'error'} label={health.database} />
          </div>
          <div class="info-row">
            <span class="label">TTS Model</span>
            <span>{health.tts_model}</span>
          </div>
          <div class="info-row">
            <span class="label">GPU Available</span>
            <span>{health.gpu_available ? 'Yes' : 'No'}</span>
          </div>
          <div class="info-row">
            <span class="label">Voices Loaded</span>
            <span>{health.voices_loaded}</span>
          </div>
          <div class="info-row">
            <span class="label">Cache Size</span>
            <span>{health.cache_size}</span>
          </div>
        {:else}
          <p class="muted">Health data unavailable.</p>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .config-page {
    max-width: 700px;
  }

  h2 {
    margin-bottom: 20px;
  }

  .section {
    margin-bottom: 24px;
  }

  h3 {
    font-size: 1em;
    color: var(--text-secondary);
    margin-bottom: 12px;
  }

  .info-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }

  .info-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
  }

  .info-row.indent {
    padding-left: 20px;
  }

  .label {
    color: var(--text-muted);
    min-width: 140px;
    font-size: 0.85em;
    text-transform: capitalize;
  }

  .center {
    display: flex;
    justify-content: center;
    padding: 48px;
  }

  .muted {
    color: var(--text-muted);
    font-size: 0.9em;
  }
</style>
