<template>
  <section class="tp-container-fluid tp-py-3 tp-page tp-page-shell">
    <ActionBar :title="t('documents.page.title')" :subtitle="t('documents.page.subtitle')" />
    <div class="tp-doc-tabs">
      <RouterLink class="tp-doc-tab" to="/documents/upload" active-class="is-active">
        {{ t('documents.tabs.upload') }}
      </RouterLink>
      <RouterLink class="tp-doc-tab" to="/documents/manage" active-class="is-active">
        {{ t('documents.tabs.manage') }}
      </RouterLink>
      <RouterLink class="tp-doc-tab" to="/documents/history" active-class="is-active">
        {{ t('documents.tabs.history') }}
      </RouterLink>
    </div>
    <router-view />
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import ActionBar from '@/components/common/ActionBar.vue';

const { t } = useI18n();
</script>

<style scoped>
.tp-doc-tabs {
  display: inline-flex;
  gap: 8px;
  padding: 4px;
  margin-top: 0;
  margin-bottom: 12px;
  border-radius: var(--tp-radius-md);
  background: var(--tp-bg-surface);
  border: 1px solid var(--tp-border-default);
}

.tp-doc-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: var(--tp-radius-sm);
  color: var(--tp-color-text-600);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}

.tp-doc-tab:hover {
  color: var(--tp-color-primary-700);
  background: color-mix(in srgb, var(--tp-color-primary-600) 10%, transparent);
}

.tp-doc-tab.is-active {
  color: var(--tp-color-primary-700);
  background: color-mix(in srgb, var(--tp-color-primary-600) 16%, transparent);
}
</style>

