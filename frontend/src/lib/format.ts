// Format an ISO date string to a short locale representation.
export function formatDate(isoString: string | null | undefined): string {
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

// Format milliseconds to a human-readable duration, showing "cached" for zero.
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) {
    return '-';
  }
  if (ms === 0) {
    return 'cached';
  }
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

// Format seconds to a human-readable uptime string.
export function formatUptime(seconds: number | null | undefined): string {
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

// Format a byte count to a human-readable string (B, KB, MB).
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes === 0) {
    return '0 B';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Truncate text to a max length with ellipsis.
export function truncate(text: string | null | undefined, max: number = 50): string {
  if (!text) {
    return '';
  }
  if (text.length <= max) {
    return text;
  }
  return text.slice(0, max) + '...';
}
