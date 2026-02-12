<script lang="ts">
  let { open = false, title = 'Confirm', message = '', onconfirm = () => {}, oncancel = () => {} }: {
    open?: boolean;
    title?: string;
    message?: string;
    onconfirm?: () => void | Promise<void>;
    oncancel?: () => void;
  } = $props();

  // Close the modal when clicking the overlay or pressing Escape.
  function handleOverlayKeydown(e: KeyboardEvent): void {
    if (e.key === 'Escape') {
      oncancel();
    }
  }
</script>

{#if open}
  <div class="overlay" role="presentation" onclick={oncancel} onkeydown={handleOverlayKeydown}>
    <div class="modal" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" tabindex="-1">
      <h3>{title}</h3>
      <div class="body">
        <p>{message}</p>
      </div>
      <div class="actions">
        <button class="btn" onclick={oncancel}>Cancel</button>
        <button class="btn-primary" onclick={onconfirm}>Confirm</button>
      </div>
    </div>
  </div>
{/if}

<style lang="scss">
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

    .body {
      margin-bottom: 20px;
      color: var(--text-secondary);
    }

    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
  }

  h3 {
    margin-bottom: 12px;
    font-size: 1.1em;
  }
</style>
