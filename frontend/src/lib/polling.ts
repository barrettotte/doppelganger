// Start a visibility-aware polling loop that pauses when the tab is hidden.
export function startPolling(fn: () => Promise<void>, intervalMs: number): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = true;

  // Schedule the next poll after the given interval.
  function schedule(): void {
    if (!running) {
      return;
    }
    timer = setTimeout(async () => {
      if (document.visibilityState === 'visible') {
        try {
          await fn();
        } catch (e) {
          console.error('Polling error:', e);
        }
      }
      schedule();
    }, intervalMs);
  }

  // Run immediately, then schedule
  fn().catch((e: unknown) => console.error('Polling error:', e));
  schedule();

  // Re-poll immediately when the tab becomes visible again.
  function onVisibilityChange(): void {
    if (document.visibilityState === 'visible') {
      fn().catch((e: unknown) => console.error('Polling error:', e));
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange);

  return function stop(): void {
    running = false;

    if (timer) {
      clearTimeout(timer);
    }
    document.removeEventListener('visibilitychange', onVisibilityChange);
  };
}
