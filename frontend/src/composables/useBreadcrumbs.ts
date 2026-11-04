import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { appNavGroups } from '@/config/navigation';

/** 子路由 Tab 对应的 i18n 键（面包屑末级） */
const TAB_TITLE_KEYS: Record<string, string> = {
  '/documents/upload': 'documents.tabs.upload',
  '/documents/manage': 'documents.tabs.manage',
  '/documents/history': 'documents.tabs.history',
  '/knowledge/upload': 'knowledge.tabs.upload',
  '/knowledge/files': 'knowledge.tabs.files',
  '/knowledge/search': 'knowledge.tabs.search',
  '/cases/generate': 'cases.tabs.generate',
  '/cases/manage': 'cases.tabs.manage'
};

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

function findSectionForPath(path: string) {
  for (const group of appNavGroups) {
    for (const item of group.items) {
      if (item.sectionPrefix && path.startsWith(item.sectionPrefix)) {
        return item;
      }
    }
  }
  return null;
}

export function useBreadcrumbs() {
  const route = useRoute();
  const { t } = useI18n();

  return computed((): BreadcrumbItem[] => {
    const path = route.path.replace(/\/+$/, '') || '/';
    const items: BreadcrumbItem[] = [
      {
        label: t('common.nav.dashboard'),
        to: path === '/' ? undefined : '/'
      }
    ];

    if (path === '/') {
      return items;
    }

    const section = findSectionForPath(path);
    const tabKey = TAB_TITLE_KEYS[path];

    if (section?.sectionLabelKey) {
      const titleKey = route.meta.titleKey as string | undefined;
      items.push({
        label: t(section.sectionLabelKey),
        to: tabKey ? section.to : undefined
      });
      if (tabKey) {
        const preferTitle = path === '/documents/history' && titleKey;
        let leafKey = preferTitle ? titleKey! : tabKey;
        if (path === '/cases/generate') {
          leafKey = route.query.kind === 'batch' ? 'cases.batch.title' : 'cases.single.title';
        }
        items.push({ label: t(leafKey) });
      } else {
        const titleKeyOnly = route.meta.titleKey as string | undefined;
        if (titleKeyOnly && section.sectionLabelKey) {
          const sectionLabel = t(section.sectionLabelKey);
          const pageLabel = t(titleKeyOnly);
          if (pageLabel !== sectionLabel) {
            items.push({ label: pageLabel });
          }
        }
      }
      return items;
    }

    const titleKey = route.meta.titleKey as string | undefined;
    if (titleKey) {
      items.push({ label: t(titleKey) });
    }

    return items;
  });
}
