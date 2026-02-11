import { toasts } from './toast';

// Start a visibility-aware polling loop that pauses when the tab is hidden.
export function startPolling(fn: () => Promise<void>, intervalMs: number): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = true;

  // Format an unknown error into a displayable string.
  function formatError(e: unknown): string {
    return e instanceof Error ? e.message : String(e);
  }

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
          toasts.error(formatError(e));
        }
      }
      schedule();
    }, intervalMs);
  }

  // Run immediately, then schedule.
  fn().catch((e: unknown) => toasts.error(formatError(e)));
  schedule();

  // Re-poll immediately when the tab becomes visible again.
  function onVisibilityChange(): void {
    if (document.visibilityState === 'visible') {
      fn().catch((e: unknown) => toasts.error(formatError(e)));
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
