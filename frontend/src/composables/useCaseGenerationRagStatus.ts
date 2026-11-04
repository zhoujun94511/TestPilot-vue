import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { getCaseConfig } from '@/api/cases';
import { useAppStore } from '@/stores';

/** 用例生成是否走知识库增强，只看配置中心 ENABLE_CASE_GENERATION_RAG。 */
export function useCaseGenerationRagStatus() {
  const { t } = useI18n();
  const appStore = useAppStore();
  const enabled = ref(false);
  const loaded = ref(false);
  const vectorEnabled = computed(() => appStore.featureFlags.enableVectorStore);

  const label = computed(() => {
    if (!loaded.value && vectorEnabled.value) return '';
    if (!vectorEnabled.value) return t('cases.form.ragUnavailable');
    return enabled.value ? t('cases.form.ragFollowsConfigOn') : t('cases.form.ragFollowsConfigOff');
  });

  async function refresh() {
    if (!vectorEnabled.value) {
      enabled.value = false;
      loaded.value = true;
      return;
    }
    try {
      const config = await getCaseConfig();
      enabled.value = Boolean(config.enable_case_generation_rag);
    } catch {
      enabled.value = false;
    } finally {
      loaded.value = true;
    }
  }

  return { enabled, label, refresh };
}
