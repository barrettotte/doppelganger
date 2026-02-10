// Start a visibility-aware polling loop that pauses when the tab is hidden.
export function startPolling(fn, intervalMs) {
  let timer = null;
  let running = true;

  // Schedule the next poll after the given interval.
  function schedule() {
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
  fn().catch((e) => console.error('Polling error:', e));
  schedule();

  // Re-poll immediately when the tab becomes visible again.
  function onVisibilityChange() {
    if (document.visibilityState === 'visible') {
      fn().catch((e) => console.error('Polling error:', e));
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange);

  return function stop() {
    running = false;
    if (timer) {
      clearTimeout(timer);
    }
    document.removeEventListener('visibilitychange', onVisibilityChange);
  };
}
