<template>
  <AppTooltipProvider>
  <div :class="shellRootClass({ collapsed: sidebarCollapsedVisual })">
    <div
      v-if="mobileNavOpen"
      :class="shellSidebarBackdropClass"
      aria-hidden="true"
      @click="closeMobileNav"
    />

    <aside :class="shellSidebarClass(mobileNavOpen)" :aria-label="t('common.shell.mainNav')">
      <div :class="shellBrandHeaderClass(sidebarCollapsedVisual)">
        <div :class="shellBrandBlockClass(sidebarCollapsedVisual)">
          <div :class="shellBrandMarkClass">
            <BrandMark size="lg" decorative />
          </div>
          <div v-show="!sidebarCollapsedVisual" :class="shellBrandTextClass">
            <div :class="brandNameClass">{{ t('common.app.brand') }}</div>
            <div :class="brandSubtitleClass" :title="t('common.app.subtitle')">
              {{ t('common.app.subtitle') }}
            </div>
          </div>
        </div>
        <button
          type="button"
          :class="shellCollapseBtnClass()"
          :title="collapseSidebarTitle"
          :aria-label="collapseSidebarTitle"
          @click="toggleSidebarCollapsed"
        >
          <PanelLeftClose v-if="!sidebarCollapsedVisual" :size="18" :stroke-width="2" />
          <PanelLeft v-else :size="18" :stroke-width="2" />
        </button>
      </div>

      <div :class="shellSidebarBodyClass">
        <nav :class="shellMainNavClass">
          <section
            v-for="group in navGroups"
            :key="group.titleKey"
            :class="shellNavGroupClass"
          >
            <div v-show="!sidebarCollapsedVisual" :class="shellNavGroupTitleClass">
              {{ t(group.titleKey) }}
            </div>
            <div :class="shellNavListClass">
              <RouterLink
                v-for="item in group.items"
                :key="item.to"
                :to="item.to"
                :class="
                  navItemClass({
                    active: isNavItemActive(item),
                    collapsed: sidebarCollapsedVisual
                  })
                "
                :title="sidebarCollapsedVisual ? t(item.labelKey) : undefined"
                @click="closeMobileNav"
              >
                <span
                  :class="navItemIconClass({ active: isNavItemActive(item) })"
                  aria-hidden="true"
                >
                  <AppNavIcon :icon="item.icon" />
                </span>
                <span v-show="!sidebarCollapsedVisual" :class="navItemLabelClass">
                  {{ t(item.labelKey) }}
                </span>
              </RouterLink>
            </div>
          </section>
        </nav>

        <div :class="shellSidebarDockClass">
          <DropdownMenu v-if="showAccountActions" :modal="false">
            <DropdownMenuTrigger as-child>
              <button
                type="button"
                :class="[
                  navItemClass({ collapsed: sidebarCollapsedVisual }),
                  shellSidebarAccountTriggerClass
                ]"
                :title="sidebarCollapsedVisual ? t('common.shell.account') : undefined"
                :aria-label="t('common.shell.account')"
              >
                <span :class="navItemIconClass()" aria-hidden="true">
                  <AppNavIcon :icon="CircleUser" />
                </span>
                <span v-show="!sidebarCollapsedVisual" :class="navItemLabelClass">
                  {{ t('common.shell.account') }}
                </span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent class="max-w-[11rem]" side="top" align="start" :side-offset="8">
              <DropdownMenuLabel class="line-clamp-2 break-all text-center" :title="signedInLabel">
                {{ signedInLabel }}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="justify-center" @select="changePasswordOpen = true">
                <KeyRound />
                {{ t('auth.password.title') }}
              </DropdownMenuItem>
              <DropdownMenuItem class="justify-center" @select="handleLogout">
                <LogOut />
                {{ t('common.shell.logout') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <ChangePasswordDialog
            v-if="showAccountActions"
            :model-value="changePasswordOpen || mustChangePassword"
            :required="mustChangePassword"
            @update:model-value="changePasswordOpen = $event"
          />

          <footer
            v-show="!sidebarCollapsedVisual"
            :class="shellSidebarFooterClass"
            :aria-label="t('common.shell.sidebarFooter')"
          >
            <p :class="shellSidebarCopyrightClass">
              {{ sidebarCopyrightLine }}
            </p>
          </footer>
        </div>
      </div>
    </aside>

    <div :class="[shellWorkspaceClass, mobileNavOpen ? 'relative z-[29]' : '']">
      <header ref="topbarEl" :class="shellTopbarClass">
        <div :class="shellTopbarLeftClass">
          <button
            type="button"
            :class="[topbarIconBtnClass(), 'max-[1199px]:inline-flex min-[1200px]:hidden']"
            :title="t('common.shell.openMenu')"
            :aria-label="t('common.shell.openMenu')"
            @click="openMobileNav"
          >
            <Menu :size="20" :stroke-width="2" />
          </button>
          <div class="min-w-0">
            <AppBreadcrumb />
            <div v-if="showPageTitle" :class="pageContextClass">{{ pageTitle }}</div>
          </div>
        </div>

        <div :class="shellTopbarActionsClass">
          <span class="sr-only" aria-live="polite">
            {{ appStore.loading ? t('common.shell.system.busy') : t('common.shell.system.ready') }}
          </span>
          <ProjectSwitcher />
          <LanguageSwitcher />
          <button
            type="button"
            :class="topbarIconBtnClass()"
            :title="`${themeToggleTitle} (${themeModeLabel})`"
            :aria-label="`${themeToggleTitle}. ${appStore.theme === 'dark' ? t('common.shell.theme.dark') : t('common.shell.theme.light')}`"
            @click="toggleTheme"
          >
            <Sun v-if="appStore.theme === 'dark'" :size="20" :stroke-width="2" />
            <Moon v-else :size="20" :stroke-width="2" />
          </button>
          <button
            v-if="mobileNavOpen"
            type="button"
            :class="[topbarIconBtnClass(), 'max-[1199px]:inline-flex min-[1200px]:hidden']"
            :title="t('common.shell.closeMenu')"
            :aria-label="t('common.shell.closeMenu')"
            @click="closeMobileNav"
          >
            <X :size="20" :stroke-width="2" />
          </button>
        </div>
      </header>

      <main :class="shellContentClass">
        <router-view v-slot="{ Component, route: activeRoute }">
          <component :is="Component" v-if="Component && !mustChangePassword" :key="shellModuleKey(activeRoute)" />
        </router-view>
      </main>
    </div>

    <AppToastStack />
  </div>
  </AppTooltipProvider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ChangePasswordDialog from '@/components/auth/ChangePasswordDialog.vue';
import { useI18n } from 'vue-i18n';
import {
  CircleUser,
  KeyRound,
  LogOut,
  Menu,
  Moon,
  PanelLeft,
  PanelLeftClose,
  Sun,
  X
} from '@lucide/vue';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { appNavGroups, type AppNavItem } from '@/config/navigation';
import { refreshAppFeatureFlags } from '@/composables/useFeatureFlags';
import { useTokenSessionNotice } from '@/composables/useTokenSessionNotice';
import BrandMark from '@/components/brand/BrandMark.vue';
import AppNavIcon from '@/components/shell/AppNavIcon.vue';
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue';
import AppTooltipProvider from '@/components/layout/AppTooltipProvider.vue';
import AppToastStack from '@/components/layout/AppToastStack.vue';
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue';
import ProjectSwitcher from '@/components/shell/ProjectSwitcher.vue';
import { useBreadcrumbs } from '@/composables/useBreadcrumbs';
import {
  brandNameClass,
  brandSubtitleClass,
  pageContextClass
} from '@/lib/page-typography';
import {
  navItemClass,
  navItemIconClass,
  navItemLabelClass,
  shellBrandBlockClass,
  shellBrandHeaderClass,
  shellBrandMarkClass,
  shellBrandTextClass,
  shellCollapseBtnClass,
  shellSidebarAccountTriggerClass,
  shellSidebarDockClass,
  shellContentClass,
  shellMainNavClass,
  shellSidebarBodyClass,
  shellSidebarCopyrightClass,
  shellSidebarFooterClass,
  shellNavGroupClass,
  shellNavGroupTitleClass,
  shellNavListClass,
  shellRootClass,
  shellSidebarBackdropClass,
  shellSidebarClass,
  shellTopbarActionsClass,
  shellTopbarClass,
  shellTopbarLeftClass,
  shellWorkspaceClass,
  topbarIconBtnClass
} from '@/lib/shell-ui';
import { shellModuleKey } from '@/lib/route-view-props';
import { useAppStore, useAuthStore } from '@/stores';
import type { AppNavRole } from '@/config/navigation';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const authStore = useAuthStore();
const breadcrumbs = useBreadcrumbs();

const mobileNavOpen = ref(false);
const changePasswordOpen = ref(false);

function navItemVisible(roles?: AppNavRole[]) {
  if (!roles?.length) return true;
  if (!authStore.authRequired) return false;
  const role = authStore.user?.role;
  return Boolean(role && roles.includes(role));
}

const navGroups = computed(() =>
  appNavGroups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => navItemVisible(item.roles) && (!item.featureFlag || appStore.featureFlags[item.featureFlag])
      )
    }))
    .filter((group) => group.items.length > 0)
);

const sidebarCollapsedVisual = computed(
  () => appStore.sidebarCollapsed && !mobileNavOpen.value
);

const showAccountActions = computed(
  () => authStore.authRequired && authStore.isAuthenticated
);
const mustChangePassword = computed(() => Boolean(authStore.user?.must_change_password));

const signedInLabel = computed(() =>
  t('common.shell.signedInAs', { name: authStore.user?.username || '' })
);

const pageTitle = computed(() => {
  const key = String(route.meta.titleKey || 'dashboard.page.title');
  return t(key);
});

/**
 * 顶栏大标题：面包屑已表达「模块 / Tab / 当前页」时不再插入 route.meta.title。
 */
const showPageTitle = computed(() => {
  const items = breadcrumbs.value;
  if (!items.length) return false;
  const lastLabel = items[items.length - 1]?.label?.trim() || '';
  if (lastLabel === pageTitle.value.trim()) return false;
  if (items.length >= 2) return false;
  return true;
});

const collapseSidebarTitle = computed(() => {
  if (mobileNavOpen.value) return t('common.shell.closeMenu');
  return appStore.sidebarCollapsed
    ? t('common.shell.expandSidebar')
    : t('common.shell.collapseSidebar');
});

const themeToggleTitle = computed(() =>
  appStore.theme === 'dark' ? t('common.shell.switchToLight') : t('common.shell.switchToDark')
);

const themeModeLabel = computed(() =>
  appStore.theme === 'dark' ? t('common.shell.theme.darkShort') : t('common.shell.theme.lightShort')
);

const COPYRIGHT_START_YEAR = 2025;

function formatCopyrightYearRange(startYear: number, endYear: number) {
  if (endYear <= startYear) return String(startYear);
  return `${startYear}–${endYear}`;
}

const sidebarCopyrightLine = computed(() =>
  t('common.shell.sidebarCopyright', {
    yearRange: formatCopyrightYearRange(COPYRIGHT_START_YEAR, new Date().getFullYear()),
    brand: t('common.app.brand')
  })
);

function isNavItemActive(item: AppNavItem) {
  if (item.to === '/') {
    return route.path === '/' || route.path === '/dashboard';
  }
  return route.path === item.to || route.path.startsWith(`${item.to}/`);
}

const MOBILE_NAV_QUERY = '(max-width: 1199px)';

function toggleSidebarCollapsed() {
  if (window.matchMedia(MOBILE_NAV_QUERY).matches) {
    closeMobileNav();
    return;
  }
  appStore.setSidebarCollapsed(!appStore.sidebarCollapsed);
}

function openMobileNav() {
  mobileNavOpen.value = true;
}

function closeMobileNav() {
  mobileNavOpen.value = false;
}

function toggleTheme() {
  appStore.setTheme(appStore.theme === 'dark' ? 'light' : 'dark');
}

async function handleLogout() {
  await authStore.logout();
  if (authStore.authRequired) {
    await router.push({ name: 'login' });
  }
}

watch(
  () => route.fullPath,
  () => {
    closeMobileNav();
  }
);

useTokenSessionNotice();

const topbarEl = ref<HTMLElement | null>(null);
let topbarObserver: ResizeObserver | null = null;

function syncDrawerTopOffset() {
  const topbar = topbarEl.value;
  if (!topbar) return;
  const bottom = Math.ceil(topbar.getBoundingClientRect().bottom);
  document.documentElement.style.setProperty('--tp-preview-top-offset', `${bottom}px`);
}

onMounted(() => {
  void refreshAppFeatureFlags();
  syncDrawerTopOffset();
  if (typeof ResizeObserver !== 'undefined' && topbarEl.value) {
    topbarObserver = new ResizeObserver(() => syncDrawerTopOffset());
    topbarObserver.observe(topbarEl.value);
  }
  window.addEventListener('resize', syncDrawerTopOffset);
});

onUnmounted(() => {
  topbarObserver?.disconnect();
  window.removeEventListener('resize', syncDrawerTopOffset);
});
</script>
