<template>
  <BaseState
    variant="info"
    :title="t('knowledge.banner.vectorDisabledStateTitle')"
    :message="t('knowledge.banner.vectorDisabledStateMessage')"
    :class="props.class"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';

const props = defineProps<{
  class?: string;
}>();

const { t } = useI18n();
</script>
