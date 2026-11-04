import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';

type MetaKey = 'titleKey' | 'subtitleKey';

function resolveMetaKey(route: ReturnType<typeof useRoute>, key: MetaKey): string | undefined {
  for (let index = route.matched.length - 1; index >= 0; index -= 1) {
    const value = route.matched[index]?.meta?.[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }
  return undefined;
}

export function useRoutePageMeta() {
  const route = useRoute();
  const { t } = useI18n();

  const pageTitle = computed(() => {
    const titleKey = resolveMetaKey(route, 'titleKey') || 'dashboard.page.title';
    return t(titleKey);
  });

  const pageSubtitle = computed(() => {
    const subtitleKey = resolveMetaKey(route, 'subtitleKey');
    return subtitleKey ? t(subtitleKey) : '';
  });

  return {
    pageTitle,
    pageSubtitle
  };
}
