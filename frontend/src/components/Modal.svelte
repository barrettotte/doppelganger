<script>
  let { open = false, title = 'Confirm', message = '', onconfirm = () => {}, oncancel = () => {} } = $props();

  // Close the modal when clicking the overlay or pressing Escape.
  function handleOverlayKeydown(e) {
    if (e.key === 'Escape') {
      oncancel();
    }
  }
</script>

{#if open}
  <div class="overlay" role="button" tabindex="0" onclick={oncancel} onkeydown={handleOverlayKeydown}>
    <div class="modal" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" tabindex="-1">
      <h3>{title}</h3>
      <div class="body">
        <p>{message}</p>
      </div>
      <div class="actions">
        <button class="btn-cancel" onclick={oncancel}>Cancel</button>
        <button class="btn-confirm" onclick={onconfirm}>Confirm</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    min-width: 360px;
    max-width: 480px;
    box-shadow: var(--shadow);
  }

  h3 {
    margin-bottom: 12px;
    font-size: 1.1em;
  }

  .body {
    margin-bottom: 20px;
    color: var(--text-secondary);
  }

  .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  button {
    padding: 6px 16px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    font-size: 0.9em;
  }

  .btn-cancel {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .btn-cancel:hover {
    background: var(--bg-hover);
  }

  .btn-confirm {
    background: var(--accent);
    color: var(--bg-primary);
    border-color: var(--accent);
  }

  .btn-confirm:hover {
    background: var(--accent-hover);
  }
</style>
