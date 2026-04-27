<template>
  <router-view />
</template>

<script setup lang="ts">
import { watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAppStore } from './stores';

const { locale } = useI18n();
const appStore = useAppStore();

watch(
  () => appStore.locale,
  (nextLocale) => {
    if (nextLocale && nextLocale !== locale.value) {
      locale.value = nextLocale;
    }
    document.documentElement.lang = nextLocale || locale.value;
  },
  { immediate: true }
);
</script>

