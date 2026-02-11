<script lang="ts">
  import { get, post, del, getBlob } from '../lib/api';
  import { formatBytes, truncate } from '../lib/format';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  let cacheState: any = $state(null);
  let loading = $state(true);
  let error = $state('');
  let playingKey: string | null = $state(null);
  let audioUrl: string | null = $state(null);

  let modalOpen = $state(false);
  let modalTitle = $state('');
  let modalMessage = $state('');
  let modalAction: () => void | Promise<void> = $state(() => {});

  // Fetch the current cache state from the API.
  async function refresh(): Promise<void> {
    try {
      cacheState = await get('/api/cache');
      error = '';
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  // Toggle the cache enabled/disabled state.
  async function handleToggle(): Promise<void> {
    if (!cacheState) {
      return;
    }
    try {
      await post('/api/cache/toggle', { enabled: !cacheState.enabled });
      await refresh();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  // Open a confirmation modal to flush all cache entries.
  function confirmFlush(): void {
    modalTitle = 'Flush Cache';
    modalMessage = `Remove all ${cacheState?.entry_count ?? 0} cached entries?`;
    modalAction = async () => {
      try {
        await post('/api/cache/flush');
        modalOpen = false;
        await refresh();

      } catch (e) {
        error = e instanceof Error ? e.message : String(e);
        modalOpen = false;
      }
    };
    modalOpen = true;
  }

  // Open a confirmation modal to delete a single cache entry.
  function confirmDelete(key: string, character: string): void {
    modalTitle = 'Delete Entry';
    modalMessage = `Remove cached entry for "${character}"?`;
    modalAction = async () => {
      try {
        await del(`/api/cache/${key}`);
        modalOpen = false;
        await refresh();

      } catch (e) {
        error = e instanceof Error ? e.message : String(e);
        modalOpen = false;
      }
    };
    modalOpen = true;
  }

  // Play a cached audio file inline.
  async function handlePlay(key: string): Promise<void> {
    if (playingKey === key) {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      playingKey = null;
      audioUrl = null;
      return;
    }
    try {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      const blob = await getBlob(`/api/cache/${key}/download`);
      audioUrl = URL.createObjectURL(blob);
      playingKey = key;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  // Download a cached audio file.
  async function handleDownload(key: string, character: string): Promise<void> {
    try {
      const blob = await getBlob(`/api/cache/${key}/download`);
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = `${character}_${key.slice(0, 8)}.wav`;
      a.click();

      URL.revokeObjectURL(url);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  // Format an epoch timestamp to a short locale string.
  function formatEpoch(epoch: number | null | undefined): string {
    if (!epoch) {
      return '-';
    }
    const d = new Date(epoch * 1000);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  refresh();
</script>

<div class="cache-page">
  <div class="page-header">
    <h2>Cache</h2>
    <div class="header-actions">
      {#if cacheState}
        <label class="toggle">
          <input type="checkbox" checked={cacheState.enabled} onchange={handleToggle} />
          {cacheState.enabled ? 'Enabled' : 'Disabled'}
        </label>
        <button class="btn btn-danger" onclick={confirmFlush} disabled={cacheState.entry_count === 0}>
          Flush All
        </button>
      {/if}
    </div>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if cacheState}
    <div class="stats">
      <div class="stat-card">
        <span class="stat-label">Entries</span>
        <span class="stat-value">{cacheState.entry_count} / {cacheState.max_size}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Total Size</span>
        <span class="stat-value">{formatBytes(cacheState.total_bytes)}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Status</span>
        <span class="stat-value badge" class:badge-ok={cacheState.enabled} class:badge-off={!cacheState.enabled}>
          {cacheState.enabled ? 'Active' : 'Disabled'}
        </span>
      </div>
    </div>

    {#if cacheState.entries.length === 0}
      <EmptyState message="Cache is empty" />
    {:else}
      <table>
        <thead>
          <tr>
            <th>Character</th>
            <th>Text</th>
            <th>Size</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each cacheState.entries as entry}
            <tr>
              <td>{entry.character}</td>
              <td class="text-cell" title={entry.text}>{truncate(entry.text, 40)}</td>
              <td>{formatBytes(entry.byte_size)}</td>
              <td>{formatEpoch(entry.created_at)}</td>
              <td class="actions-cell">
                <button class="btn-sm btn-success" onclick={() => handlePlay(entry.key)}>
                  {playingKey === entry.key ? 'Stop' : 'Play'}
                </button>
                <button class="btn-sm btn-info" onclick={() => handleDownload(entry.key, entry.character)}>Download</button>
                <button class="btn-sm btn-danger" onclick={() => confirmDelete(entry.key, entry.character)}>Delete</button>
              </td>
            </tr>
            {#if playingKey === entry.key && audioUrl}
              <tr class="player-row">
                <td colspan="5">
                  <AudioPlayer src={audioUrl} />
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    {/if}
  {/if}
</div>

<Modal open={modalOpen} title={modalTitle} message={modalMessage}
  onconfirm={modalAction} oncancel={() => (modalOpen = false)}
/>

<style lang="scss">
  .cache-page {
    max-width: 1000px;
  }

  h2 {
    margin-bottom: 0;
  }

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .stats {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 20px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 120px;
  }

  .stat-label {
    font-size: 0.8em;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-value {
    font-size: 1.1em;
    font-weight: 600;
  }

  .badge {
    font-size: 0.85em;
    font-weight: 600;

    &-ok {
      color: var(--success, #9ece6a);
    }

    &-off {
      color: var(--text-muted);
    }
  }

  .text-cell {
    max-width: 240px;
  }

  .center {
    padding: 24px;
  }

  .actions-cell {
    white-space: nowrap;
  }

  .player-row {
    td {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border);
      padding: 4px 12px 8px;
    }

    &:hover td {
      background: var(--bg-secondary);
    }
  }
</style>
