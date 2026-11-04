<template>
  <div :class="languageSwitcherClass">
    <TpButton
      size="sm"
      variant="secondary"
      :aria-label="languageToggleAriaLabel"
      :title="languageToggleTitle"
      @click="toggleLanguage"
    >
      {{ languageToggleText }}
    </TpButton>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores';
import type { Locale } from '@/i18n';
import TpButton from '@/components/ui/base/TpButton.vue';
import { languageSwitcherClass } from '@/lib/shell-ui';

const appStore = useAppStore();
const { t } = useI18n();

const languageToggleText = computed(() =>
  appStore.locale === 'zh-CN' ? t('common.language.enShort') : t('common.language.zhShort')
);

const languageToggleTitle = computed(() =>
  appStore.locale === 'zh-CN' ? t('common.shell.switchToEnglish') : t('common.shell.switchToChinese')
);

const languageToggleAriaLabel = computed(() => {
  const current =
    appStore.locale === 'zh-CN' ? t('common.language.zhCn') : t('common.language.en');
  return `${t('common.language.label')}: ${current}. ${languageToggleTitle.value}. ${t('common.language.unsupportedTraditional')}`;
});

function toggleLanguage() {
  const nextLocale: Locale = appStore.locale === 'zh-CN' ? 'en' : 'zh-CN';
  appStore.setLocale(nextLocale);
}
</script>
