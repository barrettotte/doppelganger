import { writable } from 'svelte/store';

export type ToastType = 'error' | 'success';

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

let nextId = 0;

// Reactive store holding the list of active toast notifications.
const { subscribe, update } = writable<Toast[]>([]);

// Add a toast that auto-dismisses after a delay. Skips duplicates.
function add(type: ToastType, message: string, duration: number): void {
  let duplicate = false;

  update((toasts) => {
    if (toasts.some((t) => t.message === message)) {
      duplicate = true;
    }
    return toasts;
  });

  if (duplicate) {
    return;
  }

  const id = nextId++;
  update((toasts) => [...toasts, { id, type, message }]);
  setTimeout(() => dismiss(id), duration);
}

// Add an error toast.
function error(message: string, duration = 5000): void {
  add('error', message, duration);
}

// Add a success toast.
function success(message: string, duration = 3000): void {
  add('success', message, duration);
}

// Remove a toast by its id.
function dismiss(id: number): void {
  update((toasts) => toasts.filter((t) => t.id !== id));
}

export const toasts = { subscribe, error, success, dismiss };
