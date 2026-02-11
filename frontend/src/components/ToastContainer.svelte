<script lang="ts">
  import { toasts } from '../lib/toast';
</script>

{#if $toasts.length > 0}
  <div class="toast-container">
    {#each $toasts as toast (toast.id)}
      <div class="toast" class:toast-error={toast.type === 'error'} class:toast-success={toast.type === 'success'}>
        <span class="toast-message">{toast.message}</span>
        <button class="toast-close" onclick={() => toasts.dismiss(toast.id)}>x</button>
      </div>
    {/each}
  </div>
{/if}

<style lang="scss">
  .toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 400px;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: var(--bg-secondary);
    border-radius: var(--radius);
    padding: 10px 14px;
    font-size: 0.9em;
    box-shadow: var(--shadow);
    animation: slide-in 0.2s ease-out;
  }

  .toast-error {
    border: 1px solid var(--error);
    color: var(--error);
  }

  .toast-success {
    border: 1px solid var(--success);
    color: var(--success);
  }

  .toast-message {
    flex: 1;
    word-break: break-word;
  }

  .toast-close {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 0.85em;
    padding: 0 2px;
    line-height: 1;

    &:hover {
      color: var(--text-primary);
    }
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateX(20px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
</style>
