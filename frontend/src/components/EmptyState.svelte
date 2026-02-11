<script lang="ts">
  let { message = 'No data to display' }: { message?: string } = $props();
</script>

<div class="empty">
  <p>{message}</p>
</div>

<style lang="scss">
  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    color: var(--text-muted);
    font-size: 0.95em;
  }
</style>
