<script lang="ts">
  import type { Snippet } from 'svelte';
  import Header from './Header.svelte';
  import Sidebar from './Sidebar.svelte';
  import ToastContainer from './ToastContainer.svelte';

  let { children }: { children: Snippet } = $props();
</script>

<div class="layout">
  <Sidebar />
  <div class="main-area">
    <Header />
    <main>
      {@render children()}
    </main>
  </div>
</div>
<ToastContainer />

<style lang="scss">
  .layout {
    display: flex;
    height: 100vh;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  main {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }
</style>
