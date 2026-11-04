<template>
  <nav
    :class="cn(pageTabsNavClass, props.class)"
    role="tablist"
    :aria-label="ariaLabel || undefined"
    @keydown="handleTabListKeydown"
  >
    <RouterLink
      v-for="(tab, index) in tabs"
      :key="tabKey(tab, index)"
      :ref="(el) => setTabRef(index, el)"
      :to="tab.to"
      :class="pageTabItemClass({ active: isTabActive(tab) })"
      role="tab"
      :aria-selected="isTabActive(tab)"
      :tabindex="isTabActive(tab) ? 0 : -1"
    >
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import type { RouteLocationRaw, RouteLocationNormalizedLoaded } from 'vue-router';
import { useRoute, useRouter } from 'vue-router';
import type { ComponentPublicInstance } from 'vue';
import { shallowRef } from 'vue';
import { cn } from '@/lib/utils';
import { pageTabItemClass, pageTabsNavClass } from '@/lib/panel-ui';

export interface PageTabItem {
  to: RouteLocationRaw;
  label: string;
  match?: (route: RouteLocationNormalizedLoaded) => boolean;
}

const props = withDefaults(
  defineProps<{
    tabs: PageTabItem[];
    ariaLabel?: string;
    class?: string;
  }>(),
  {
    ariaLabel: '',
    class: ''
  }
);

const route = useRoute();
const router = useRouter();
const tabRefs = shallowRef<Array<HTMLElement | null>>([]);

function normalizePath(path: string) {
  return path.replace(/\/+$/, '') || '/';
}

function tabPath(to: RouteLocationRaw) {
  return typeof to === 'string' ? to : String(to.path || '');
}

function tabKey(tab: PageTabItem, index: number) {
  const path = tabPath(tab.to);
  const query =
    typeof tab.to === 'object' && tab.to && 'query' in tab.to
      ? JSON.stringify(tab.to.query ?? {})
      : '';
  return `${path}${query}-${index}`;
}

function isTabActive(tab: PageTabItem) {
  if (tab.match) return tab.match(route);
  return normalizePath(route.path) === normalizePath(tabPath(tab.to));
}

function setTabRef(index: number, el: Element | ComponentPublicInstance | null) {
  const node = el instanceof HTMLElement ? el : (el as ComponentPublicInstance | null)?.$el;
  tabRefs.value[index] = node instanceof HTMLElement ? node : null;
}

function focusTab(index: number) {
  const target = tabRefs.value[index];
  target?.focus();
}

function activateTab(index: number) {
  const tab = props.tabs[index];
  if (!tab) return;
  if (!isTabActive(tab)) {
    void router.push(tab.to);
  }
  focusTab(index);
}

function handleTabListKeydown(event: KeyboardEvent) {
  const { key } = event;
  if (!props.tabs.length) return;

  let activeIndex = props.tabs.findIndex((tab) => isTabActive(tab));
  if (activeIndex < 0) activeIndex = 0;

  if (key === ' ' || key === 'Spacebar') {
    event.preventDefault();
    activateTab(activeIndex);
    return;
  }

  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(key)) return;

  event.preventDefault();

  let nextIndex = activeIndex;
  if (key === 'Home') nextIndex = 0;
  else if (key === 'End') nextIndex = props.tabs.length - 1;
  else if (key === 'ArrowRight') nextIndex = (activeIndex + 1) % props.tabs.length;
  else nextIndex = (activeIndex - 1 + props.tabs.length) % props.tabs.length;

  activateTab(nextIndex);
}
</script>
