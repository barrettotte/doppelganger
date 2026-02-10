<script>
  let { src = null } = $props();
</script>

{#if src}
  <div class="player">
    <audio controls src={src}></audio>
  </div>
{/if}

<style>
  .player {
    margin: 8px 0;
  }

  audio {
    width: 100%;
    max-width: 360px;
    height: 36px;
  }
</style>
