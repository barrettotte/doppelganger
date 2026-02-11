<script lang="ts">
  let { status = 'unknown', label = '' }: { status?: string; label?: string } = $props();

  const colorMap: Record<string, string> = {
    ok: 'var(--success)',
    healthy: 'var(--success)',
    connected: 'var(--success)',
    completed: 'var(--success)',
    processing: 'var(--accent)',
    pending: 'var(--warning)',
    degraded: 'var(--warning)',
    warning: 'var(--warning)',
    cancelled: 'var(--text-muted)',
    failed: 'var(--error)',
    error: 'var(--error)',
    disconnected: 'var(--error)',
  };

  let color = $derived(colorMap[status] || 'var(--text-muted)');
  let text = $derived(label || status);
</script>

<span class="badge" style="--dot-color: {color}">
  <span class="dot"></span>
  {text}
</span>

<style lang="scss">
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85em;
    text-transform: capitalize;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--dot-color);
    flex-shrink: 0;
  }
</style>
