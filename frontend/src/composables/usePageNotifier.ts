import {
  usePageNotice,
  type PageNoticeOptions,
  type PageNoticeType
} from '@/composables/usePageNotice';

/** 与 `notify` 相同，但不包含 type / message */
export type PageNoticeExtras = Omit<PageNoticeOptions, 'type' | 'message'>;

/**
 * 页面级反馈统一入口：Toast / Banner 路由规则见 usePageNotice。
 * 调用约定：showNotice(type, message, extras?)
 */
export function usePageNotifier() {
  const pageNotice = usePageNotice();

  function showNotice(type: PageNoticeType, message: string, extras?: PageNoticeExtras) {
    pageNotice.notify({
      type,
      message,
      ...extras
    });
  }

  return {
    ...pageNotice,
    showNotice
  };
}
