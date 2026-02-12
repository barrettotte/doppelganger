<script lang="ts">
  import { onDestroy } from 'svelte';
  import { get } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { startPolling } from '../lib/polling';
  import { formatUptime, formatBytes } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import Spinner from '../components/Spinner.svelte';

  let stats: any = $state(null);
  let health: any = $state(null);
  let botStatus: any = $state(null);
  let loading = $state(true);

  // Fetch system stats, health, and bot status in parallel.
  async function refresh() {
    try {
      const [s, h, b] = await Promise.all([
        get('/api/system/stats'),
        get('/health'),
        get('/api/status'),
      ]);
      stats = s;
      health = h;
      botStatus = b;
    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      loading = false;
    }
  }

  const stop = startPolling(refresh, 10000);
  onDestroy(stop);

  // Format VRAM percent as a CSS width value.
  function vramWidth(gpu: any): string {
    return `${Math.min(gpu.vram_percent, 100)}%`;
  }

  // Format hit rate as a percentage string.
  function hitRatePercent(rate: number): string {
    return `${(rate * 100).toFixed(1)}%`;
  }
</script>

<div class="system">
  <h2>System</h2>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if stats}
    <div class="section">
      <h3>Health</h3>
      <div class="health-items">
        <div class="health-item">
          <span class="health-label">Status</span>
          <StatusBadge status={health?.status ?? 'unknown'} />
        </div>
        <div class="health-item">
          <span class="health-label">Database</span>
          <StatusBadge status={health?.database === 'connected' ? 'connected' : 'disconnected'} label={health?.database ?? 'unknown'} />
        </div>
        <div class="health-item">
          <span class="health-label">TTS Model</span>
          <StatusBadge status={health?.tts_model === 'loaded' ? 'ok' : 'warning'} label={health?.tts_model ?? 'unknown'} />
        </div>
        <div class="health-item">
          <span class="health-label">GPU</span>
          <StatusBadge status={health?.gpu_available ? 'ok' : 'warning'} label={health?.gpu_available ? 'available' : 'unavailable'} />
        </div>
        <div class="health-item">
          <span class="health-label">Bot</span>
          <StatusBadge status={botStatus?.connected ? 'connected' : 'disconnected'} label={botStatus?.connected ? 'online' : 'offline'} />
        </div>
      </div>
    </div>

    {#if stats.gpus.length > 0}
      <div class="section">
        <h3>GPUs</h3>
        <div class="gpu-cards">
          {#each stats.gpus as gpu}
            <div class="card gpu-card">
              <div class="gpu-header">
                <span class="gpu-name">{gpu.name}</span>
                <span class="gpu-index">GPU {gpu.index}</span>
              </div>
              <div class="vram-bar-container">
                <div class="vram-bar" style="width: {vramWidth(gpu)}"></div>
              </div>
              <div class="gpu-details">
                <span>VRAM: {gpu.vram_used_mb} / {gpu.vram_total_mb} MB ({gpu.vram_percent}%)</span>
                {#if gpu.utilization_percent != null}
                  <span>Utilization: {gpu.utilization_percent}%</span>
                {/if}
                {#if gpu.temperature_c != null}
                  <span>Temp: {gpu.temperature_c}C</span>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <div class="section">
      <h3>Engines</h3>
      {#if stats.engines.length === 0}
        <p class="muted">No engines registered.</p>
      {:else}
        <div class="engines">
          {#each stats.engines as eng}
            <div class="engine-item">
              <StatusBadge
                status={eng.loaded ? 'connected' : 'disconnected'}
                label={eng.engine}
              />
              <span class="engine-detail">{eng.device}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="section">
      <h3>Overview</h3>
      <div class="cards">
        <div class="card">
          <div class="card-label">Uptime</div>
          <div class="card-value">{formatUptime(stats.uptime_seconds)}</div>
        </div>
        <div class="card">
          <div class="card-label">Queue Depth</div>
          <div class="card-value">{stats.queue_depth}</div>
        </div>
        <div class="card">
          <div class="card-label">Voices Loaded</div>
          <div class="card-value">{stats.voices_loaded}</div>
        </div>
      </div>
    </div>

    <div class="section">
      <h3>Cache</h3>
      <div class="cards">
        <div class="card">
          <div class="card-label">Hit Rate</div>
          <div class="card-value">{hitRatePercent(stats.cache_hit_rate)}</div>
        </div>
        <div class="card">
          <div class="card-label">Hits</div>
          <div class="card-value success">{stats.cache_hits}</div>
        </div>
        <div class="card">
          <div class="card-label">Misses</div>
          <div class="card-value error">{stats.cache_misses}</div>
        </div>
        <div class="card">
          <div class="card-label">Entries</div>
          <div class="card-value">{stats.cache_size}</div>
        </div>
        <div class="card">
          <div class="card-label">Total Size</div>
          <div class="card-value">{formatBytes(stats.cache_total_bytes)}</div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style lang="scss">
  .system {
    max-width: 1000px;
  }

  .section {
    margin-bottom: 32px;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }

  .card-label {
    font-size: 0.8em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .card-value {
    font-size: 1.4em;
    font-weight: 600;

    &.success {
      color: var(--success);
    }

    &.error {
      color: var(--error);
    }
  }

  .gpu-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }

  .gpu-card {
    padding: 16px;
  }

  .gpu-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .gpu-name {
    font-weight: 600;
    font-size: 0.95em;
  }

  .gpu-index {
    font-size: 0.8em;
    color: var(--text-muted);
  }

  .vram-bar-container {
    width: 100%;
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 10px;
  }

  .vram-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .gpu-details {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.8em;
    color: var(--text-secondary);
  }

  .engines {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .engine-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 16px;
  }

  .engine-detail {
    font-size: 0.8em;
    color: var(--text-muted);
  }

  .health-items {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .health-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 16px;
  }

  .health-label {
    font-size: 0.8em;
    color: var(--text-muted);
  }

  .muted {
    color: var(--text-muted);
    padding: 12px 0;
  }
</style>
