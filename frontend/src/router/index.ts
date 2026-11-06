import { createRouter, createWebHistory } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import i18n from '@/i18n';
import { pinia, useAppStore, useAuthStore } from '@/stores';
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
const LoginView = () => import('@/views/LoginView.vue');
const UsersAdminView = () => import('@/views/UsersAdminView.vue');

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
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: {
      titleKey: 'auth.page.title',
      public: true
    }
  },
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
          titleKey: 'config.page.title',
          roles: ['super_admin']
        }
      },
      {
        path: 'admin/users',
        name: 'admin-users',
        component: UsersAdminView,
        meta: {
          titleKey: 'admin.users.page.title',
          roles: ['super_admin', 'admin']
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
        path: 'experimental-tools',
        name: 'experimental-tools',
        component: () => import('@/views/ExperimentalToolsView.vue'),
        meta: {
          titleKey: 'experimentalToolsPage.page.title'
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
    document.title = `${appName} - ${i18n.global.t(titleKey)}`;
  } else {
    document.title = appName;
  }
}

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);
  if (!authStore.bootstrapped) {
    try {
      await authStore.bootstrap();
    } catch {
      // 后端暂时不可用：按需要登录处理，未登录时落到登录页，下次导航再重试
    }
  }

  if (to.name === 'login') {
    if (authStore.authRequired && authStore.isAuthenticated) {
      return { path: '/' };
    }
    return true;
  }

  if (authStore.authRequired && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath }
    };
  }

  const roles = to.meta.roles as string[] | undefined;
  if (authStore.authRequired && roles?.length) {
    const currentRole = authStore.user?.role;
    if (!currentRole || !roles.includes(currentRole)) {
      return { path: '/' };
    }
  }

  return true;
});

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
