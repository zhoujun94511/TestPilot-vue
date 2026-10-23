import { createRouter, createWebHistory } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import i18n from '@/i18n';
import { pinia, useAppStore } from '@/stores';
import type { RouteLocationNormalizedLoaded } from 'vue-router';

const DashboardView = () => import('@/views/DashboardView.vue');
const ChatView = () => import('@/views/ChatView.vue');
const CasesView = () => import('@/views/CasesView.vue');
const CasesShellView = () => import('@/views/CasesShellView.vue');
const ConfigCenterView = () => import('@/views/ConfigCenterView.vue');
const DocumentsShellView = () => import('@/views/DocumentsShellView.vue');
const DocumentsUploadView = () => import('@/views/DocumentsUploadView.vue');
const DocumentsView = () => import('@/views/DocumentsView.vue');
const DocumentsHistoryView = () => import('@/views/DocumentsHistoryView.vue');
const KnowledgeShellView = () => import('@/views/KnowledgeShellView.vue');
const KnowledgeUploadView = () => import('@/views/KnowledgeUploadView.vue');
const KnowledgeView = () => import('@/views/KnowledgeView.vue');
const KnowledgeSearchView = () => import('@/views/KnowledgeSearchView.vue');

function resolveBasePath(): string {
  const metaBase = document
    .querySelector<HTMLMetaElement>('meta[name="testpilot-base-path"]')
    ?.content?.trim();

  const rawBase = metaBase && metaBase !== '__TESTPILOT_BASE_PATH__'
    ? metaBase
    : import.meta.env.BASE_URL || '/';

  const normalized = rawBase.startsWith('/') ? rawBase : `/${rawBase}`;
  return normalized.length > 1 ? normalized.replace(/\/+$/, '') : '/';
}

const routes = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
        meta: {
          titleKey: 'dashboard.page.title'
        }
      },
      {
        path: 'dashboard',
        redirect: '/'
      },
      {
        path: 'config',
        name: 'config',
        component: ConfigCenterView,
        meta: {
          titleKey: 'config.page.title'
        }
      },
      {
        path: 'knowledge',
        component: KnowledgeShellView,
        children: [
          {
            path: '',
            redirect: '/knowledge/upload'
          },
          {
            path: 'upload',
            name: 'knowledge-upload',
            component: KnowledgeUploadView,
            meta: {
              titleKey: 'knowledge.page.title'
            }
          },
          {
            path: 'files',
            name: 'knowledge',
            component: KnowledgeView,
            meta: {
              titleKey: 'knowledge.page.title'
            }
          },
          {
            path: 'search',
            name: 'knowledge-search',
            component: KnowledgeSearchView,
            meta: {
              titleKey: 'knowledge.page.title'
            }
          }
        ]
      },
      {
        path: 'documents',
        component: DocumentsShellView,
        children: [
          {
            path: '',
            redirect: '/documents/upload'
          },
          {
            path: 'upload',
            name: 'documents-upload',
            component: DocumentsUploadView,
            meta: {
              titleKey: 'documents.page.title'
            }
          },
          {
            path: 'manage',
            name: 'documents',
            component: DocumentsView,
            meta: {
              titleKey: 'documents.page.title'
            }
          },
          {
            path: 'history',
            name: 'documents-history',
            component: DocumentsHistoryView,
            meta: {
              titleKey: 'documents.history.title'
            }
          }
        ]
      },
      {
        path: 'chat',
        name: 'chat',
        component: ChatView,
        meta: {
          titleKey: 'chat.page.title'
        }
      },
      {
        path: 'cases',
        component: CasesShellView,
        children: [
          {
            path: '',
            redirect: '/cases/generate'
          },
          {
            path: 'generate',
            name: 'cases-generate',
            component: CasesView,
            props: { mode: 'generate' },
            meta: {
              titleKey: 'cases.page.title'
            }
          },
          {
            path: 'manage',
            name: 'cases-manage',
            component: CasesView,
            props: { mode: 'manage' },
            meta: {
              titleKey: 'cases.page.title'
            }
          }
        ]
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(resolveBasePath()),
  routes
});

export function updateDocumentTitle(route: RouteLocationNormalizedLoaded) {
  const titleKey = route.meta.titleKey as string | undefined;
  const appName = String(i18n.global.t('common.app.brand') || 'TestPilot');
  if (titleKey) {
    document.title = `${i18n.global.t(titleKey)} - ${appName}`;
  } else {
    document.title = appName;
  }
}

router.afterEach((to) => {
  const appStore = useAppStore(pinia);
  updateDocumentTitle(to);
  document.documentElement.lang = appStore.locale || i18n.global.locale.value;
});

router.onError((error) => {
  const message = String((error as Error)?.message || '');
  const isChunkLoadError = message.includes('Failed to fetch dynamically imported module')
    || message.includes('Unable to preload CSS');
  if (!isChunkLoadError) return;

  // Auto-recover once when client holds stale chunk hash after deployment.
  const key = 'tp.chunk_reload_once';
  try {
    const reloaded = sessionStorage.getItem(key) === '1';
    if (!reloaded) {
      sessionStorage.setItem(key, '1');
      window.location.reload();
      return;
    }
    sessionStorage.removeItem(key);
  } catch {
    window.location.reload();
  }
});

export default router;
