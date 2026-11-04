<template>
  <section :class="pageFluidShellSectionClass()">
    <PageTabs :tabs="tabs" :aria-label="t('documents.page.title')" />
    <router-view />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import PageTabs from '@/components/common/PageTabs.vue';
import { pageFluidShellSectionClass } from '@/lib/page-layout-ui';

const { t } = useI18n();

const tabs = computed(() => [
  { to: '/documents/upload', label: t('documents.tabs.upload') },
  { to: '/documents/manage', label: t('documents.tabs.manage') },
  { to: '/documents/history', label: t('common.nav.documentHistory') }
]);
</script>
