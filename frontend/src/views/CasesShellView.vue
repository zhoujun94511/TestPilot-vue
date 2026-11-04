<template>
  <section :class="pageFluidShellSectionClass()">
    <PageTabs class="mb-4" :tabs="tabs" :aria-label="t('cases.page.title')" />
    <router-view />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import PageTabs, { type PageTabItem } from '@/components/common/PageTabs.vue';
import { pageFluidShellSectionClass } from '@/lib/page-layout-ui';

const { t } = useI18n();

const tabs = computed((): PageTabItem[] => [
  {
    to: '/cases/generate',
    label: t('cases.single.title'),
    match: (route) => route.path === '/cases/generate' && route.query.kind !== 'batch'
  },
  {
    to: { path: '/cases/generate', query: { kind: 'batch' } },
    label: t('cases.batch.title'),
    match: (route) => route.path === '/cases/generate' && route.query.kind === 'batch'
  },
  {
    to: '/cases/manage',
    label: t('cases.tabs.manage')
  }
]);
</script>
