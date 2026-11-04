<template>
  <section :class="pageFluidShellSectionClass()">
    <PageNoticeBanner
      v-if="vectorNotice"
      :notice="vectorNotice"
      @close="dismissVectorNotice"
      @action="openConfigCenter"
    />
    <PageTabs :tabs="tabs" :aria-label="t('knowledge.page.title')" />
    <router-view />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PageTabs from '@/components/common/PageTabs.vue';
import { pageFluidShellSectionClass } from '@/lib/page-layout-ui';
import { refreshAppFeatureFlags } from '@/composables/useFeatureFlags';
import { useKnowledgeVectorNotice } from '@/composables/useKnowledgeVectorNotice';

const { t } = useI18n();
const {
  notice: vectorNotice,
  dismissNotice: dismissVectorNotice,
  openConfigCenter,
  resetDismissIfVectorEnabled
} = useKnowledgeVectorNotice();

onMounted(() => {
  void refreshAppFeatureFlags().then(() => resetDismissIfVectorEnabled());
});

const tabs = computed(() => [
  { to: '/knowledge/upload', label: t('knowledge.tabs.upload') },
  { to: '/knowledge/files', label: t('knowledge.tabs.files') },
  { to: '/knowledge/search', label: t('knowledge.tabs.search') }
]);
</script>
