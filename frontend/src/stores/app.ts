import { defineStore } from 'pinia';
import type { Locale } from '@/i18n';

export interface FeatureFlags {
  enableVectorStore: boolean;
  experimentalActionsEnabled: boolean;
}

export type AppTheme = 'light' | 'dark';

export interface ToastMessage {
  id: number;
  type: 'success' | 'danger' | 'warning' | 'info';
  title?: string;
  message: string;
  timeout?: number;
}

export const useAppStore = defineStore('app', {
  state: () => ({
    locale: (localStorage.getItem('testpilot_locale') as Locale) || 'zh-CN',
    theme: (localStorage.getItem('testpilot_theme') as AppTheme) || 'light',
    loading: false,
    featureFlags: {
      enableVectorStore: true,
      experimentalActionsEnabled: false
    } as FeatureFlags,
    sidebarCollapsed: localStorage.getItem('testpilot_sidebar_collapsed') === '1',
    toasts: [] as ToastMessage[]
  }),
  actions: {
    setLocale(locale: Locale) {
      this.locale = locale;
      localStorage.setItem('testpilot_locale', locale);
    },
    setTheme(theme: AppTheme) {
      this.theme = theme;
      localStorage.setItem('testpilot_theme', theme);
    },
    setLoading(loading: boolean) {
      this.loading = loading;
    },
    setFeatureFlags(flags: Partial<FeatureFlags>) {
      this.featureFlags = {
        ...this.featureFlags,
        ...flags
      };
    },
    setSidebarCollapsed(collapsed: boolean) {
      this.sidebarCollapsed = collapsed;
      localStorage.setItem('testpilot_sidebar_collapsed', collapsed ? '1' : '0');
    },
    pushToast(toast: Omit<ToastMessage, 'id'>) {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      this.toasts.push({
        id,
        timeout: 4500,
        ...toast
      });
      return id;
    },
    removeToast(id: number) {
      this.toasts = this.toasts.filter((toast) => toast.id !== id);
    },
    clearToasts() {
      this.toasts = [];
    }
  }
});
