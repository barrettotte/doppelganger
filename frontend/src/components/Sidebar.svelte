<script lang="ts">
  import { location } from 'svelte-spa-router';

  const links = [
    { path: '/', label: 'Dashboard' },
    { path: '/queue', label: 'Queue' },
    { path: '/cache', label: 'Cache' },
    { path: '/characters', label: 'Characters' },
    { path: '/users', label: 'Users' },
    { path: '/config', label: 'Config' },
    { path: '/metrics', label: 'Metrics' },
  ];

  // Check if a nav link matches the current route path.
  function isActive(linkPath: string, currentPath: string): boolean {
    if (linkPath === '/') {
      return currentPath === '/';
    }
    return currentPath.startsWith(linkPath);
  }
</script>

<nav>
  <ul>
    {#each links as link}
      <li>
        <a href="#{link.path}" class:active={isActive(link.path, $location)}>
          {link.label}
        </a>
      </li>
    {/each}
  </ul>
</nav>

<style lang="scss">
  nav {
    width: var(--sidebar-width);
    height: 100%;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    padding: 16px 0;
    flex-shrink: 0;
  }

  ul {
    list-style: none;
  }

  a {
    display: block;
    padding: 10px 20px;
    color: var(--text-secondary);
    font-size: 0.95em;
    transition: background 0.15s, color 0.15s;

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    &.active {
      color: var(--accent);
      background: var(--bg-tertiary);
      border-left: 3px solid var(--accent);
      padding-left: 17px;
    }
  }
</style>
