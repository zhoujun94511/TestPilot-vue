<template>
  <BrandMark v-if="icon === 'brand-mark'" size="xs" decorative />
  <component v-else :is="icon" :size="18" :stroke-width="2" />
</template>

<script setup lang="ts">
import BrandMark from '@/components/brand/BrandMark.vue';
import type { AppNavIcon } from '@/config/navigation';

defineProps<{
  icon: AppNavIcon;
}>();
</script>
