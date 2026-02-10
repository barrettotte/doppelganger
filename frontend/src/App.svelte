<script>
  import Router from 'svelte-spa-router';
  import Layout from './components/Layout.svelte';
  import Dashboard from './pages/Dashboard.svelte';
  import Queue from './pages/Queue.svelte';
  import Users from './pages/Users.svelte';
  import UserDetail from './pages/UserDetail.svelte';
  import Characters from './pages/Characters.svelte';
  import Config from './pages/Config.svelte';
  import Metrics from './pages/Metrics.svelte';

  const routes = {
    '/': Dashboard,
    '/queue': Queue,
    '/users': Users,
    '/users/:id': UserDetail,
    '/characters': Characters,
    '/config': Config,
    '/metrics': Metrics,
  };
</script>

<Layout>
  {#snippet children()}
    <Router {routes} />
  {/snippet}
</Layout>
