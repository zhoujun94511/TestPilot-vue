<template>
  <div class="tp-shell">
    <aside class="tp-sidebar">
      <div class="tp-brand">
        <div class="tp-brand-mark">
          <img class="tp-brand-mark__icon" :src="robotLogo" alt="TestPilot" />
        </div>
        <div>
          <div class="tp-brand-name">TestPilot</div>
          <div class="tp-brand-subtitle">{{ t('common.app.subtitle') }}</div>
        </div>
      </div>

      <nav>
        <section v-for="group in navGroups" :key="group.title" class="tp-nav-group">
          <div class="tp-nav-group-title">{{ group.title }}</div>
          <div class="tp-nav-list">
            <RouterLink
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              class="tp-nav-item"
            >
              <span class="tp-nav-item-icon" aria-hidden="true">{{ item.icon }}</span>
              <span class="tp-nav-item-label">{{ item.label }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>

    </aside>

    <div class="tp-workspace">
      <header class="tp-topbar">
        <div class="tp-topbar-left">
          <div class="tp-page-kicker">{{ pageKicker }}</div>
          <div class="tp-page-context">{{ pageContext }}</div>
        </div>

        <div class="tp-topbar-actions">
          <button
            class="tp-topbar-icon-btn"
            type="button"
            :title="languageToggleTitle"
            :aria-label="languageToggleTitle"
            @click="toggleLanguage"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="m5 8 6 6" />
              <path d="m4 14 6-6 2-3" />
              <path d="M2 5h12" />
              <path d="M7 2h1" />
              <path d="m22 22-5-10-5 10" />
              <path d="M14 18h6" />
            </svg>
            <span class="tp-topbar-lang">{{ languageToggleText }}</span>
          </button>
          <button
            class="tp-topbar-icon-btn"
            type="button"
            :title="themeToggleTitle"
            :aria-label="themeToggleTitle"
            @click="toggleTheme"
          >
            <svg v-if="appStore.theme === 'dark'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2" />
              <path d="M12 20v2" />
              <path d="m4.93 4.93 1.41 1.41" />
              <path d="m17.66 17.66 1.41 1.41" />
              <path d="M2 12h2" />
              <path d="M20 12h2" />
              <path d="m6.34 17.66-1.41 1.41" />
              <path d="m19.07 4.93-1.41 1.41" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401" />
            </svg>
          </button>
          <button
            class="tp-topbar-icon-btn"
            type="button"
            :title="t('common.nav.configCenter')"
            :aria-label="t('common.nav.configCenter')"
            @click="openConfigCenter"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        </div>
      </header>

      <main class="tp-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores';
import robotLogo from '@/assets/robot.svg';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const appStore = useAppStore();

const navGroups = computed(() =>
  [
    {
      title: t('common.shell.groups.overview'),
      items: [
        { to: '/', label: t('common.nav.dashboard'), icon: 'DB' }
      ]
    },
    {
      title: t('common.shell.groups.analysis'),
      items: [
        { to: '/documents', label: t('common.nav.documents'), icon: 'DO' },
        { to: '/knowledge', label: t('common.nav.knowledgeBase'), icon: 'KB' }
      ]
    },
    {
      title: t('common.shell.groups.generation'),
      items: [
        { to: '/cases', label: t('common.nav.cases'), icon: 'CS' }
      ]
    },
    {
      title: t('common.shell.groups.assistant'),
      items: [
        { to: '/chat', label: t('common.nav.chat'), icon: 'AI' }
      ]
    },
    {
      title: t('common.shell.groups.system'),
      items: []
    }
  ].filter((group) => group.items.length > 0)
);

const pageKicker = computed(() => t('common.shell.pageKicker'));
const pageContext = computed(() => {
  const key = String(route.meta.titleKey || 'dashboard.page.title');
  return t(key);
});

const languageToggleText = computed(() => (appStore.locale === 'zh-CN' ? 'en' : 'zh'));
const languageToggleTitle = computed(() =>
  appStore.locale === 'zh-CN' ? t('common.shell.switchToEnglish') : t('common.shell.switchToChinese')
);
const themeToggleTitle = computed(() =>
  appStore.theme === 'dark' ? t('common.shell.switchToLight') : t('common.shell.switchToDark')
);

function toggleTheme() {
  appStore.setTheme(appStore.theme === 'dark' ? 'light' : 'dark');
}

function toggleLanguage() {
  const nextLocale = appStore.locale === 'zh-CN' ? 'en' : 'zh-CN';
  appStore.setLocale(nextLocale);
  document.documentElement.lang = nextLocale;
}

function openConfigCenter() {
  router.push('/config');
}
</script>

<style scoped>
.tp-topbar-actions {
  display: flex;
  align-items: center;
  gap: var(--tp-space-2);
}

.tp-topbar-icon-btn {
  border: 1px solid transparent;
  border-radius: var(--tp-radius-sm);
  background: transparent;
  color: var(--tp-color-text-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 36px;
  min-height: 36px;
  padding: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tp-topbar-icon-btn:hover {
  color: var(--tp-color-primary-600);
  background: color-mix(in srgb, var(--tp-color-primary-600) 10%, transparent);
}

.tp-topbar-icon-btn:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--tp-color-primary-600) 40%, white);
  outline-offset: 2px;
}

.tp-topbar-lang {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.tp-brand-mark__icon {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
</style>
