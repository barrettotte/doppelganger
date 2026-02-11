<script lang="ts">
  import { onMount } from 'svelte';
  import { get, post } from '../lib/api';
  import { formatDate, formatDuration } from '../lib/format';
  import StatusBadge from '../components/StatusBadge.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  let { params = {} }: { params?: { id?: string } } = $props();
  let userId = $derived(params.id);

  let users: any[] = $state([]);
  let user: any = $state(null);
  let requests: any[] = $state([]);
  let loading = $state(true);

  let modalOpen = $state(false);
  let modalTitle = $state('');
  let modalMessage = $state('');
  let modalAction: () => void | Promise<void> = $state(() => {});

  // Fetch the user info and their TTS request history.
  async function loadData() {
    try {
      const usersData = await get('/api/users');
      users = usersData.users;
      user = users.find((u) => u.id === Number(userId)) || null;

      if (user) {
        const data = await get(`/api/users/${userId}/requests`);
        requests = data.requests;
      }

    } catch (e) {
      console.error('Failed to load user detail:', e);
    } finally {
      loading = false;
    }
  }

  onMount(loadData);

  // Open a confirmation modal to toggle this user's blacklist status.
  function confirmToggle() {
    if (!user) {
      return;
    }
    const newState = !user.blacklisted;
    modalTitle = newState ? 'Blacklist User' : 'Unblacklist User';
    modalMessage = `${newState ? 'Blacklist' : 'Unblacklist'} user ${user.discord_id}?`;

    modalAction = async () => {
      await post(`/api/users/${user.id}/blacklist`, { blacklisted: newState });
      modalOpen = false;
      await loadData();
    };
    modalOpen = true;
  }
</script>

<div class="user-detail">
  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if !user}
    <EmptyState message="User not found" />
  {:else}
    <div class="header-row">
      <h2>User: {user.username ?? user.discord_id}</h2>
      <a href="#/users">Back to Users</a>
    </div>

    <div class="info-card">
      <div class="info-row">
        <span class="info-label">ID</span>
        <span>{user.id}</span>
      </div>
      {#if user.username}
        <div class="info-row">
          <span class="info-label">Username</span>
          <span>{user.username}</span>
        </div>
      {/if}
      <div class="info-row">
        <span class="info-label">Discord ID</span>
        <code>{user.discord_id}</code>
      </div>
      <div class="info-row">
        <span class="info-label">Status</span>
        {#if user.blacklisted}
          <StatusBadge status="error" label="Blacklisted" />
        {:else}
          <StatusBadge status="ok" label="Active" />
        {/if}
      </div>
      <div class="info-row">
        <span class="info-label">Created</span>
        <span>{formatDate(user.created_at)}</span>
      </div>
      <div class="info-row">
        <button class="btn-sm" class:btn-danger={!user.blacklisted} onclick={confirmToggle}>
          {user.blacklisted ? 'Unblacklist' : 'Blacklist'}
        </button>
      </div>
    </div>

    <h3>Request History ({requests.length})</h3>
    {#if requests.length === 0}
      <EmptyState message="No requests from this user" />
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
          {#each requests as req}
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
  {/if}
</div>

<Modal open={modalOpen} title={modalTitle} message={modalMessage}
  onconfirm={modalAction} oncancel={() => (modalOpen = false)}
/>

<style lang="scss">
  .user-detail {
    max-width: 900px;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  .info-card {
    margin-bottom: 24px;
  }

  .info-label {
    min-width: 100px;
  }
</style>
