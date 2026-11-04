import { useAppStore } from '@/stores';
import type { ToastMessage } from '@/stores/app';

type ToastInput = Omit<ToastMessage, 'id'>;

export function useToast() {
  const appStore = useAppStore();

  function push(toast: ToastInput) {
    return appStore.pushToast(toast);
  }

  function success(message: string, title?: string) {
    return push({ type: 'success', message, title });
  }

  function error(message: string, title?: string) {
    return push({ type: 'danger', message, title });
  }

  function warning(message: string, title?: string) {
    return push({ type: 'warning', message, title });
  }

  function info(message: string, title?: string) {
    return push({ type: 'info', message, title });
  }

  return {
    push,
    success,
    error,
    warning,
    info,
    dismiss: (id: number) => appStore.removeToast(id)
  };
}
