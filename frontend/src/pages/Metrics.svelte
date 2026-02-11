<script lang="ts">
  import { onDestroy } from 'svelte';
  import { get } from '../lib/api';
  import { startPolling } from '../lib/polling';
  import { fetchUserMaps } from '../lib/users';
  import { formatDate, formatDuration } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Spinner from '../components/Spinner.svelte';

  let metrics: any = $state(null);
  let auditEntries: any[] = $state([]);
  let recentRequests: any[] = $state([]);
  let loading = $state(true);
  let userById: Map<number, string> = $state(new Map());

  let auditFilter = $state('');
  let auditLimit = $state(50);

  // Fetch metrics, recent requests, and user maps for display.
  async function loadMetrics() {
    try {
      const [m, r, maps] = await Promise.all([
        get('/api/metrics'),
        get('/api/requests?limit=20'),
        fetchUserMaps(),
      ]);
      metrics = m;
      recentRequests = r.requests;
      userById = maps.byId;

    } catch (e) {
      console.error('Failed to load metrics:', e);
    } finally {
      loading = false;
    }
  }

  // Fetch audit log entries with the current filter and limit applied.
  async function loadAudit() {
    try {
      const params = new URLSearchParams({ limit: String(auditLimit) });
      if (auditFilter) {
        params.set('action', auditFilter);
      }

      const data = await get(`/api/audit?${params}`);
      auditEntries = data.entries;

    } catch (e) {
      console.error('Failed to load audit:', e);
    }
  }

  // Refresh all metrics and audit data together.
  async function refresh() {
    await Promise.all([loadMetrics(), loadAudit()]);
  }

  const stop = startPolling(refresh, 30000);
  onDestroy(stop);

  // Update the audit action filter and reload audit entries.
  function handleAuditFilterChange(e: Event): void {
    auditFilter = (e.target as HTMLSelectElement).value;
    loadAudit();
  }

  // Update the audit entry limit and reload audit entries.
  function handleAuditLimitChange(e: Event): void {
    auditLimit = Number((e.target as HTMLSelectElement).value);
    loadAudit();
  }
</script>

<div class="metrics-page">
  <h2>Metrics</h2>

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
        <div class="card-label">Cancelled</div>
        <div class="card-value">{metrics?.cancelled ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Avg Duration</div>
        <div class="card-value">{formatDuration(metrics?.avg_duration_ms)}</div>
      </div>
      <div class="card">
        <div class="card-label">Queue Depth</div>
        <div class="card-value">{metrics?.queue_depth ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Cache Size</div>
        <div class="card-value">{metrics?.cache_size ?? 0}</div>
      </div>
      <div class="card">
        <div class="card-label">Voices Loaded</div>
        <div class="card-value">{metrics?.voices_loaded ?? 0}</div>
      </div>
    </div>

    <div class="two-col">
      <div class="section">
        <h3>Requests by Character</h3>
        {#if metrics && Object.keys(metrics.requests_by_character).length > 0}
          <table>
            <thead>
              <tr><th>Character</th><th>Count</th></tr>
            </thead>
            <tbody>
              {#each Object.entries(metrics.requests_by_character) as [char, count]}
                <tr><td>{char}</td><td>{count}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState message="No data" />
        {/if}
      </div>

      <div class="section">
        <h3>Top Users</h3>
        {#if metrics && metrics.top_users.length > 0}
          <table>
            <thead>
              <tr><th>User</th><th>Requests</th></tr>
            </thead>
            <tbody>
              {#each metrics.top_users as entry}
                <tr><td>{userById.get(entry.user_id) ?? entry.user_id}</td><td>{entry.count}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState message="No data" />
        {/if}
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <h3>Audit Log</h3>
        <div class="audit-controls">
          <select onchange={handleAuditFilterChange} value={auditFilter}>
            <option value="">All actions</option>
            <option value="tts_generate">tts_generate</option>
            <option value="character_created">character_created</option>
            <option value="character_deleted">character_deleted</option>
            <option value="user_blacklisted">user_blacklisted</option>
          </select>
          <select onchange={handleAuditLimitChange} value={auditLimit}>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>

      {#if auditEntries.length === 0}
        <EmptyState message="No audit entries found" />
      {:else}
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>User</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {#each auditEntries as entry}
              <tr>
                <td>{formatDate(entry.created_at)}</td>
                <td><code>{entry.action}</code></td>
                <td>{entry.user_id ? (userById.get(entry.user_id) ?? entry.user_id) : '-'}</td>
                <td class="details-cell">
                  {#if entry.details}
                    <code>{JSON.stringify(entry.details)}</code>
                  {:else}
                    -
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <div class="section">
      <h3>Recent Activity</h3>
      {#if recentRequests.length === 0}
        <EmptyState message="No recent activity" />
      {:else}
        <div class="activity-feed">
          {#each recentRequests as req}
            <div class="activity-item">
              <StatusBadge status={req.status} />
              <span class="activity-text">
                #{req.id} {req.character}: "{req.text.slice(0, 40)}{req.text.length > 40 ? '...' : ''}"
              </span>
              <span class="activity-time">{formatDate(req.created_at)}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style lang="scss">
  .metrics-page {
    max-width: 1000px;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 32px;
  }

  .card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
  }

  .card-label {
    font-size: 0.8em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .card-value {
    font-size: 1.3em;
    font-weight: 600;

    &.success {
      color: var(--success);
    }

    &.error {
      color: var(--error);
    }
  }

  .two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
  }

  .audit-controls {
    display: flex;
    gap: 8px;
  }

  .details-cell {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .activity-feed {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .activity-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border-radius: var(--radius);
    font-size: 0.9em;
  }

  .activity-text {
    flex: 1;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .activity-time {
    color: var(--text-muted);
    font-size: 0.85em;
    flex-shrink: 0;
  }
</style>
