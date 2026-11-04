<template>
  <img :src="chatAssistantRobotSrc" :alt="altText" :class="[chatAssistantAvatarSizeClass(size), props.class]" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { chatAssistantRobotSrc } from '@/lib/brand';
import { chatAssistantAvatarSizeClass, type BrandMarkSize } from '@/lib/brand-ui';

const props = withDefaults(
  defineProps<{
    size?: BrandMarkSize;
    decorative?: boolean;
    class?: string;
  }>(),
  {
    size: 'md',
    decorative: false,
    class: ''
  }
);

const { t } = useI18n();

const altText = computed(() => (props.decorative ? '' : t('chat.roles.assistant')));
</script>
