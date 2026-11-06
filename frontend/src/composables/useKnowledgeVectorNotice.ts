import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import type { PageBannerNotice } from '@/composables/usePageNotice';
import { ApiError } from '@/api/http';
import { useAppStore } from '@/stores';
import { useAuthStore } from '@/stores/auth';

const DISMISS_KEY = 'tp.knowledge_vector_off_dismissed';

/** 与后端 ENABLE_VECTOR_STORE=false → 403 对齐，用于禁用上传/检索等操作 */
export function useKnowledgeVectorGate() {
  const appStore = useAppStore();
  const vectorDisabled = computed(() => !appStore.featureFlags.enableVectorStore);
  const shouldSkipKnowledgeFetch = vectorDisabled;
  return { vectorDisabled, shouldSkipKnowledgeFetch };
}

export function isVectorStoreDisabledError(error: unknown): boolean {
  const code = error instanceof ApiError ? error.code : undefined;
  const errorCode = String(error instanceof ApiError ? error.errorCode ?? '' : '').toLowerCase();
  const message = String(error instanceof Error ? error.message : '').toLowerCase();
  return code === 403
    || errorCode.includes('vector')
    || message.includes('vector_store')
    || message.includes('向量')
    || message.includes('enable_vector_store');
}

export function useKnowledgeVectorNotice() {
  const { t } = useI18n();
  const router = useRouter();
  const appStore = useAppStore();
  const authStore = useAuthStore();
  const dismissed = ref(sessionStorage.getItem(DISMISS_KEY) === '1');

  const vectorDisabled = computed(() => !appStore.featureFlags.enableVectorStore);

  const notice = computed<PageBannerNotice | null>(() => {
    if (!vectorDisabled.value || dismissed.value) return null;
    return {
      type: 'warning',
      title: t('knowledge.banner.vectorDisabledTitle'),
      message: t('knowledge.banner.vectorDisabledMessage'),
      actionLabel: authStore.canSeeConfigCenter() ? t('knowledge.banner.vectorDisabledAction') : undefined
    };
  });

  function dismissNotice() {
    dismissed.value = true;
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      // ignore
    }
  }

  function openConfigCenter() {
    if (authStore.canSeeConfigCenter()) void router.push({ name: 'config' });
  }

  /** 后端改 ENABLE_VECTOR_STORE 后应重新展示提示 */
  function resetDismissIfVectorEnabled() {
    if (appStore.featureFlags.enableVectorStore) {
      dismissed.value = false;
      try {
        sessionStorage.removeItem(DISMISS_KEY);
      } catch {
        // ignore
      }
    }
  }

  return {
    notice,
    dismissNotice,
    openConfigCenter,
    resetDismissIfVectorEnabled
  };
}
