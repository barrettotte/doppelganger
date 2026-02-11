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

  {#if loading}
    <div class="center"><Spinner /></div>
  {:else if users.length === 0}
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
        {#each users as user}
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
              <button class="btn-sm" class:btn-danger={!user.blacklisted} onclick={(e) => { e.stopPropagation(); confirmToggle(user); }}>
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

  .center {
    display: flex;
    justify-content: center;
    padding: 48px;
  }

  .clickable {
    cursor: pointer;
  }

</style>
