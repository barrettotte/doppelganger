<script lang="ts">
  import { onDestroy } from 'svelte';
  import { get } from '../lib/api';
  import { toasts } from '../lib/toast';
  import { startPolling } from '../lib/polling';
  import { formatDate, formatDuration } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import Spinner from '../components/Spinner.svelte';

  let metrics: any = $state(null);
  let recentRequests: any[] = $state([]);
  let loading = $state(true);

  // Fetch metrics and recent requests in parallel.
  async function refresh() {
    try {
      const [m, r] = await Promise.all([
        get('/api/metrics'),
        get('/api/requests?limit=10'),
      ]);
      metrics = m;
      recentRequests = r.requests;

    } catch (e) {
      toasts.error(e instanceof Error ? e.message : String(e));
    } finally {
      loading = false;
    }
  }

  const stop = startPolling(refresh, 15000);
  onDestroy(stop);

</script>

<div class="dashboard">
  <h2>Dashboard</h2>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else}
    <div class="cards">
      <div class="card">
        <div class="card-label">Total Requests</div>
        <div class="card-value">{metrics?.total_requests ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Completed</div>
        <div class="card-value success">{metrics?.completed ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Failed</div>
        <div class="card-value error">{metrics?.failed ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Avg Duration</div>
        <div class="card-value">{formatDuration(metrics?.avg_duration_ms)}</div>
      </div>
      <div class="card">
        <div class="card-label">Queue Depth</div>
        <div class="card-value">{metrics?.queue_depth ?? 0}</div>
      </div>
    </div>

    <div class="section">
      <h3>Recent Requests</h3>
      {#if recentRequests.length === 0}
        <p class="muted">No requests yet.</p>
      {:else}
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Character</th>
              <th>Text</th>
              <th>Status</th>
              <th>Created</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {#each recentRequests as req}
              <tr>
                <td>{req.id}</td>
                <td>{req.character}</td>
                <td class="text-cell">{req.text}</td>
                <td><StatusBadge status={req.status} /></td>
                <td>{formatDate(req.created_at)}</td>
                <td>{formatDuration(req.duration_ms)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}
</div>

<style lang="scss">
  .dashboard {
    max-width: 1000px;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 32px;
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

  .section {
    margin-top: 8px;
  }

  .muted {
    padding: 24px 0;
  }
</style>
