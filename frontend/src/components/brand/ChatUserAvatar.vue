<template>
  <div
    :class="cn(chatUserAvatarShellClass(size), props.class)"
    :aria-hidden="props.decorative ? 'true' : undefined"
    :role="props.decorative ? undefined : 'img'"
    :aria-label="props.decorative ? undefined : t('chat.roles.user')"
  >
    <svg viewBox="0 0 32 32" class="h-full w-full" aria-hidden="true">
      <circle cx="16" cy="12.2" r="5" fill="currentColor" />
      <path fill="currentColor" d="M5 26.2C7.2 21.4 11 19.6 16 19.6s8.8 1.8 11 6.6V36H5Z" />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { chatUserAvatarShellClass, type BrandMarkSize } from '@/lib/brand-ui';
import { cn } from '@/lib/utils';

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
</script>
