<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { formatUptime } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import Spinner from '../components/Spinner.svelte';

  let status: any = $state(null);
  let health: any = $state(null);
  let loading = $state(true);

  // Fetch bot status and system health data in parallel.
  async function loadData() {
    try {
      const [s, h] = await Promise.all([get('/api/status'), get('/health')]);
      status = s;
      health = h;

    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
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
          <span class="info-label">Connection</span>
          <StatusBadge status={status?.connected ? 'connected' : 'disconnected'} label={status?.connected ? 'Connected' : 'Disconnected'} />
        </div>
        {#if status?.connected}
          <div class="info-row">
            <span class="info-label">Username</span>
            <span>{status.username}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Guilds</span>
            <span>{status.guild_count}</span>
          </div>
          {#each status.guilds as guild}
            <div class="info-row indent">
              <span class="info-label">Guild</span>
              <span>{guild.name} ({guild.member_count} members)</span>
            </div>
          {/each}
          <div class="info-row">
            <span class="info-label">Uptime</span>
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
              <span class="info-label">{key.replace(/_/g, ' ')}</span>
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
            <span class="info-label">Status</span>
            <StatusBadge status={health.status === 'ok' ? 'ok' : 'degraded'} label={health.status} />
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
  {/if}
</div>

<style lang="scss">
  .config-page {
    max-width: 700px;
  }

  .info-row.indent {
    padding-left: 20px;
  }

  .info-label {
    min-width: 140px;
    text-transform: capitalize;
  }
</style>
