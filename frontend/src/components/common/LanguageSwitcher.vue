<template>
  <div class="tp-language-switcher">
    <TpButton
      size="sm"
      variant="secondary"
      :aria-label="languageToggleLabel"
      @click="toggleLanguage"
    >
      {{ languageToggleLabel }}
    </TpButton>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores';
import type { Locale } from '@/i18n';
import TpButton from '@/components/ui/base/TpButton.vue';

const appStore = useAppStore();
const { t } = useI18n();

const languageToggleLabel = computed(() => `${t('common.language.zhShort')} / ${t('common.language.enShort')}`);

function setLanguage(nextLocale: Locale) {
  appStore.setLocale(nextLocale);
  document.documentElement.lang = nextLocale;
}

function toggleLanguage() {
  setLanguage(appStore.locale === 'zh-CN' ? 'en' : 'zh-CN');
}
</script>
