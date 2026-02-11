<script lang="ts">
  import { onDestroy } from 'svelte';
  import { get, post } from '../lib/api';
  import { startPolling } from '../lib/polling';
  import { fetchUserMaps } from '../lib/users';
  import { formatDate, formatDuration, truncate } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  let queueState: any = $state(null);
  let history: any[] = $state([]);
  let loading = $state(true);
  let userById: Map<number, string> = $state(new Map());
  let userByDiscordId: Map<string, string> = $state(new Map());
  let statusFilter = $state('');
  let autoRefresh = $state(true);

  let modalOpen = $state(false);
  let modalTitle = $state('');
  let modalMessage = $state('');
  let modalAction: () => void | Promise<void> = $state(() => {});

  // Fetch the current queue state from the API.
  async function refreshQueue() {
    try {
      queueState = await get('/api/queue');
    } catch (e) {
      console.error('Queue refresh failed:', e);
    }
  }

  // Fetch request history with the current status filter applied.
  async function refreshHistory() {
    try {
      const params = statusFilter ? `?status=${statusFilter}&limit=50` : '?limit=50';
      const data = await get(`/api/requests${params}`);
      history = data.requests;

    } catch (e) {
      console.error('History refresh failed:', e);
    } finally {
      loading = false;
    }
  }

  // Refresh the user lookup maps for resolving IDs to display names.
  async function refreshUsers() {
    try {
      const maps = await fetchUserMaps();
      userById = maps.byId;
      userByDiscordId = maps.byDiscordId;

    } catch (e) {
      console.error('User map refresh failed:', e);
    }
  }

  // Refresh all queue data - queue state, history, and user maps.
  async function refresh() {
    await Promise.all([refreshQueue(), refreshHistory(), refreshUsers()]);
  }

  let stopPolling: (() => void) | null = null;

  // Start or stop the polling loop based on the auto-refresh toggle.
  function setupPolling(): void {
    if (stopPolling) {
      stopPolling();
    }
    if (autoRefresh) {
      stopPolling = startPolling(refresh, 5000);
    } else {
      refresh();
      stopPolling = null;
    }
  }

  $effect(() => {
    autoRefresh;
    setupPolling();
  });

  onDestroy(() => {
    if (stopPolling) {
      stopPolling();
    }
  });

  // Open a confirmation modal to cancel a queued request.
  function confirmCancel(requestId: number): void {
    modalTitle = 'Cancel Request';
    modalMessage = `Cancel request #${requestId}?`;

    modalAction = async () => {
      await post(`/api/queue/${requestId}/cancel`);
      modalOpen = false;
      await refresh();
    };
    modalOpen = true;
  }

  // Open a confirmation modal to bump a request to the front of the queue.
  function confirmBump(requestId: number): void {
    modalTitle = 'Bump Request';
    modalMessage = `Move request #${requestId} to the front of the queue?`;

    modalAction = async () => {
      await post(`/api/queue/${requestId}/bump`);
      modalOpen = false;
      await refresh();
    };
    modalOpen = true;
  }

  // Update the status filter and reload request history.
  function handleFilterChange(e: Event): void {
    statusFilter = (e.target as HTMLSelectElement).value;
    loading = true;
    refreshHistory();
  }
</script>

<div class="queue-page">
  <h2>Queue</h2>

  <div class="section">
    <div class="section-header">
      <h3>Live Queue</h3>
      <label class="toggle">
        <input type="checkbox" bind:checked={autoRefresh} />
        Auto-refresh
      </label>
    </div>

    {#if queueState}
      {#if queueState.processing}
        <div class="processing-card">
          <StatusBadge status="processing" label="Processing" />
          <span class="queue-detail">
            #{queueState.processing.request_id} - {queueState.processing.character}: "{truncate(queueState.processing.text, 40)}"
          </span>
        </div>
      {/if}

      {#if queueState.pending.length > 0}
        <table>
          <thead>
            <tr>
              <th>Position</th>
              <th>Request</th>
              <th>User</th>
              <th>Character</th>
              <th>Text</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each queueState.pending as item, i}
              <tr>
                <td>{i + 1}</td>
                <td>#{item.request_id}</td>
                <td>{userByDiscordId.get(item.discord_id) ?? item.discord_id}</td>
                <td>{item.character}</td>
                <td class="text-cell">{truncate(item.text, 30)}</td>
                <td>
                  <button class="btn-sm" onclick={() => confirmBump(item.request_id)}>Bump</button>
                  <button class="btn-sm btn-danger" onclick={() => confirmCancel(item.request_id)}>Cancel</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else if !queueState.processing}
        <EmptyState message="Queue is empty" />
      {/if}
    {:else}
      <Spinner />
    {/if}
  </div>

  <div class="section">
    <div class="section-header">
      <h3>Request History</h3>
      <select onchange={handleFilterChange} value={statusFilter}>
        <option value="">All statuses</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
        <option value="pending">Pending</option>
        <option value="processing">Processing</option>
      </select>
    </div>

    {#if loading}
      <div class="center"><Spinner /></div>
    {:else if history.length === 0}
      <EmptyState message="No requests found" />
    {:else}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Character</th>
            <th>Text</th>
            <th>Status</th>
            <th>Created</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {#each history as req}
            <tr>
              <td>{req.id}</td>
              <td>{userById.get(req.user_id) ?? req.user_id}</td>
              <td>{req.character}</td>
              <td class="text-cell">{truncate(req.text, 30)}</td>
              <td><StatusBadge status={req.status} /></td>
              <td>{formatDate(req.created_at)}</td>
              <td>{formatDuration(req.duration_ms)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

<Modal open={modalOpen} title={modalTitle} message={modalMessage}
  onconfirm={modalAction} oncancel={() => (modalOpen = false)}
/>

<style lang="scss">
  .queue-page {
    max-width: 1000px;
  }

  .section {
    margin-bottom: 32px;
  }

  h3 {
    margin-bottom: 0;
  }

  .processing-card {
    background: var(--bg-tertiary);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .queue-detail {
    color: var(--text-secondary);
    font-size: 0.9em;
  }

  .text-cell {
    max-width: 180px;
  }

  .center {
    padding: 24px;
  }
</style>
