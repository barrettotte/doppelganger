<script>
  let { columns = [], rows = [], onrowclick = null } = $props();
  let sortKey = $state('');
  let sortDir = $state(1);

  // Toggle sort direction on the given column, or set it as the new sort key.
  function handleSort(key) {
    if (sortKey === key) {
      sortDir = sortDir * -1;
    } else {
      sortKey = key;
      sortDir = 1;
    }
  }

  // Handle Enter or Space on a row to trigger the row click callback.
  function handleRowKeydown(e, row) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onrowclick?.(row);
    }
  }

  let sortedRows = $derived.by(() => {
    if (!sortKey) {
      return rows;
    }
    return [...rows].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va == null && vb == null) {
        return 0;
      }
      if (va == null) {
        return 1;
      }
      if (vb == null) {
        return -1;
      }
      if (va < vb) {
        return -1 * sortDir;
      }
      if (va > vb) {
        return 1 * sortDir;
      }
      return 0;
    });
  });
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        {#each columns as col}
          <th>
            {#if col.sortable !== false}
              <button class="sort-btn" type="button" onclick={() => handleSort(col.key)}>
                {col.label}
                {#if sortKey === col.key}
                  <span class="sort-arrow">{sortDir === 1 ? ' ^' : ' v'}</span>
                {/if}
              </button>
            {:else}
              {col.label}
            {/if}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sortedRows as row}
        <tr
          class:clickable={onrowclick != null}
          role={onrowclick != null ? 'button' : undefined}
          tabindex={onrowclick != null ? 0 : undefined}
          onclick={() => onrowclick?.(row)}
          onkeydown={(e) => handleRowKeydown(e, row)}
        >
          {#each columns as col}
            <td>
              {#if col.render}
                {@html col.render(row[col.key], row)}
              {:else}
                {row[col.key] ?? '-'}
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .table-wrap {
    overflow-x: auto;
  }

  .sort-btn {
    background: none;
    border: none;
    padding: 0;
    color: inherit;
    font: inherit;
    font-weight: inherit;
    cursor: pointer;
    white-space: nowrap;
  }

  .sort-btn:hover {
    color: var(--accent);
  }

  .sort-arrow {
    font-size: 0.8em;
  }

  .clickable {
    cursor: pointer;
  }
</style>
