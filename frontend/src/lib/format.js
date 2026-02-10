// Format an ISO date string to a short locale representation.
export function formatDate(isoString) {
  if (!isoString) {
    return '-';
  }
  const d = new Date(isoString);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Format milliseconds to a human-readable duration.
export function formatDuration(ms) {
  if (ms == null) {
    return '-';
  }
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

// Format seconds to a human-readable uptime string.
export function formatUptime(seconds) {
  if (seconds == null) {
    return '-';
  }
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);

  if (h > 0) {
    return `${h}h ${m}m`;
  }
  return `${m}m`;
}

// Truncate text to a max length with ellipsis.
export function truncate(text, max = 50) {
  if (!text) {
    return '';
  }
  if (text.length <= max) {
    return text;
  }
  return text.slice(0, max) + '...';
}
