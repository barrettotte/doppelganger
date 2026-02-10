<script>
  import Header from './Header.svelte';
  import Sidebar from './Sidebar.svelte';

  let { children } = $props();
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

<style>
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
