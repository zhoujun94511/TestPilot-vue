<template>
  <RouterLink :to="to" :class="dashboardShortcutTileClass">
    <span :class="navItemIconClass({ active: false })" aria-hidden="true">
      <AppNavIcon :icon="icon" />
    </span>
    <span class="min-w-0 flex-1">
      <span :class="dashboardShortcutTileTitleClass">{{ title }}</span>
      <span v-if="description" :class="dashboardShortcutTileDescClass">{{ description }}</span>
    </span>
  </RouterLink>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import AppNavIcon from '@/components/shell/AppNavIcon.vue';
import type { AppNavIcon as AppNavIconType } from '@/config/navigation';
import {
  dashboardShortcutTileClass,
  dashboardShortcutTileDescClass,
  dashboardShortcutTileTitleClass
} from '@/lib/dashboard-ui';
import { navItemIconClass } from '@/lib/shell-ui';

defineProps<{
  to: string;
  title: string;
  description?: string;
  icon: AppNavIconType;
}>();
</script>
