import { createApp } from 'vue';
import { watch } from 'vue';
import App from './App.vue';
import router, { updateDocumentTitle } from './router';
import i18n from './i18n';
import { onPasswordChangeRequired, onUnauthorized } from './api/http';
import { pinia, useAppStore, useAuthStore } from './stores';
import './styles/main.css';

const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(i18n);

const appStore = useAppStore(pinia);
const authStore = useAuthStore(pinia);

onUnauthorized(() => {
  if (!authStore.authRequired || !authStore.isAuthenticated) return;
  authStore.clearSession();
  const current = router.currentRoute.value;
  if (current.name === 'login') return;
  void router.replace({
    name: 'login',
    query: { redirect: current.fullPath, expired: '1' }
  });
});

onPasswordChangeRequired(() => authStore.markPasswordChangeRequired());

function applyTheme(theme: 'light' | 'dark') {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

i18n.global.locale.value = appStore.locale;
document.documentElement.lang = appStore.locale;
applyTheme(appStore.theme);

watch(
  () => appStore.theme,
  (nextTheme) => {
    applyTheme(nextTheme);
  },
  { immediate: true }
);

watch(
  () => appStore.locale,
  (nextLocale) => {
    i18n.global.locale.value = nextLocale;
    document.documentElement.lang = nextLocale;
    updateDocumentTitle(router.currentRoute.value);
  },
  { immediate: true }
);

app.mount('#app');
