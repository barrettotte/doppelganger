<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { get, post } from '../lib/api.js';
  import { formatDate } from '../lib/format.js';
  import StatusBadge from '../components/StatusBadge.svelte';
  import EmptyState from '../components/EmptyState.svelte';
  import Modal from '../components/Modal.svelte';
  import Spinner from '../components/Spinner.svelte';

  let users = $state([]);
  let loading = $state(true);
  let search = $state('');

  let modalOpen = $state(false);
  let modalTitle = $state('');
  let modalMessage = $state('');
  let modalAction = $state(() => {});

  // Fetch the full list of users from the API.
  async function loadUsers() {
    try {
      const data = await get('/api/users');
      users = data.users;
    } catch (e) {
      console.error('Failed to load users:', e);
    } finally {
      loading = false;
    }
  }

  onMount(loadUsers);

  let filteredUsers = $derived(
    search
      ? users.filter((u) =>
          u.discord_id.includes(search) ||
          (u.username && u.username.toLowerCase().includes(search.toLowerCase()))
        )
      : users
  );

  // Navigate to user detail on Enter or Space key press.
  function handleRowKeydown(e, user) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      push(`/users/${user.id}`);
    }
  }

  // Open a confirmation modal to toggle a user's blacklist status.
  function confirmToggle(user) {
    const newState = !user.blacklisted;
    modalTitle = newState ? 'Blacklist User' : 'Unblacklist User';
    modalMessage = `${newState ? 'Blacklist' : 'Unblacklist'} user ${user.discord_id}?`;

    modalAction = async () => {
      await post(`/api/users/${user.id}/blacklist`, { blacklisted: newState });
      modalOpen = false;
      await loadUsers();
    };
    modalOpen = true;
  }
</script>

<div class="users-page">
  <h2>Users</h2>

  <div class="toolbar">
    <input type="text" placeholder="Search by name or Discord ID..." bind:value={search}/>
  </div>

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if filteredUsers.length === 0}
    <EmptyState message="No users found" />
  {:else}
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Username</th>
          <th>Discord ID</th>
          <th>Blacklisted</th>
          <th>Created</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredUsers as user}
          <tr class="clickable" role="button" tabindex="0" onclick={() => push(`/users/${user.id}`)} onkeydown={(e) => handleRowKeydown(e, user)}>
            <td>{user.id}</td>
            <td>{user.username ?? '-'}</td>
            <td><code>{user.discord_id}</code></td>
            <td>
              {#if user.blacklisted}
                <StatusBadge status="error" label="Blacklisted" />
              {:else}
                <StatusBadge status="ok" label="Active" />
              {/if}
            </td>
            <td>{formatDate(user.created_at)}</td>
            <td>
              <button class="btn-small" class:btn-danger={!user.blacklisted} onclick={(e) => { e.stopPropagation(); confirmToggle(user); }}>
                {user.blacklisted ? 'Unblacklist' : 'Blacklist'}
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

<Modal open={modalOpen} title={modalTitle} message={modalMessage}
  onconfirm={modalAction} oncancel={() => (modalOpen = false)}
/>

<style>
  .users-page {
    max-width: 900px;
  }

  h2 {
    margin-bottom: 20px;
  }

  .toolbar {
    margin-bottom: 16px;
  }

  input[type="text"] {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 6px 12px;
    border-radius: var(--radius);
    width: 260px;
  }

  input[type="text"]::placeholder {
    color: var(--text-muted);
  }

  .center {
    display: flex;
    justify-content: center;
    padding: 48px;
  }

  .clickable {
    cursor: pointer;
  }

  .btn-small {
    padding: 3px 10px;
    font-size: 0.8em;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .btn-small:hover {
    background: var(--bg-hover);
  }

  .btn-danger {
    color: var(--error);
    border-color: var(--error);
  }

  .btn-danger:hover {
    background: rgba(247, 118, 142, 0.15);
  }
</style>
