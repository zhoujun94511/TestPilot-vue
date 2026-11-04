import { onBeforeUnmount, ref } from 'vue';
import { useToast } from '@/composables/useToast';

export type PageNoticeType = 'success' | 'danger' | 'warning' | 'info';

export interface PageBannerNotice {
  type: PageNoticeType;
  message: string;
  title?: string;
  actionLabel?: string;
  onAction?: () => void | Promise<void>;
  details?: string[];
}

export interface PageNoticeOptions {
  type: PageNoticeType;
  message: string;
  title?: string;
  timeout?: number;
  actionLabel?: string;
  onAction?: () => void | Promise<void>;
  details?: string[];
  /** 强制使用顶栏 Banner，不走 Toast */
  preferBanner?: boolean;
}

function mapToastType(type: PageNoticeType): 'success' | 'danger' | 'warning' | 'info' {
  if (type === 'danger') return 'danger';
  if (type === 'warning') return 'warning';
  if (type === 'info') return 'info';
  return 'success';
}

export function usePageNotice() {
  const toast = useToast();
  const banner = ref<PageBannerNotice | null>(null);
  let timer: number | null = null;

  function clearBanner() {
    banner.value = null;
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function needsBanner(input: PageNoticeOptions): boolean {
    if (input.preferBanner) return true;
    if (input.actionLabel || input.onAction) return true;
    if (input.details?.length) return true;
    return input.type === 'danger' || input.type === 'warning';
  }

  function notify(input: PageNoticeOptions) {
    if (!needsBanner(input)) {
      clearBanner();
      toast.push({
        type: mapToastType(input.type),
        title: input.title,
        message: input.message,
        timeout: input.timeout ?? 4500
      });
      return;
    }

    clearBanner();
    banner.value = {
      type: input.type,
      message: input.message,
      title: input.title,
      actionLabel: input.actionLabel,
      onAction: input.onAction,
      details: input.details
    };

    const timeout = input.timeout ?? (input.type === 'danger' ? 8000 : 5000);
    if (timeout > 0) {
      timer = window.setTimeout(() => {
        clearBanner();
      }, timeout);
    }
  }

  async function runBannerAction() {
    const action = banner.value?.onAction;
    if (!action) return;
    await action();
    clearBanner();
  }

  onBeforeUnmount(() => {
    clearBanner();
  });

  return {
    banner,
    notify,
    clearBanner,
    runBannerAction
  };
}
