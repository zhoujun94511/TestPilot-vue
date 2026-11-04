<template>
  <component
    :is="to ? RouterLink : 'div'"
    :to="to"
    :class="cn(dashboardStatTileClass, to && 'no-underline')"
  >
    <span :class="navItemIconClass({ active: false })" aria-hidden="true">
      <AppNavIcon :icon="icon" />
    </span>
    <span class="min-w-0 flex-1">
      <div v-if="valuePlacement === 'end'" :class="dashboardStatTileHeadRowClass">
        <span :class="dashboardStatTileTitleInlineClass">{{ label }}</span>
        <span :class="dashboardStatTileValueEndClass">{{ value }}</span>
      </div>
      <template v-else>
        <span :class="dashboardStatTileLabelClass">{{ label }}</span>
        <span :class="dashboardStatTileValueClass">{{ value }}</span>
      </template>
      <span v-if="hint" :class="dashboardStatTileHintClass">{{ hint }}</span>
    </span>
  </component>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import AppNavIcon from '@/components/shell/AppNavIcon.vue';
import type { AppNavIcon as AppNavIconType } from '@/config/navigation';
import {
  dashboardStatTileClass,
  dashboardStatTileHeadRowClass,
  dashboardStatTileHintClass,
  dashboardStatTileLabelClass,
  dashboardStatTileTitleInlineClass,
  dashboardStatTileValueClass,
  dashboardStatTileValueEndClass
} from '@/lib/dashboard-ui';
import { navItemIconClass } from '@/lib/shell-ui';
import { cn } from '@/lib/utils';

withDefaults(
  defineProps<{
    label: string;
    value: string | number;
    hint?: string;
    to?: string;
    icon: AppNavIconType;
    /** stack：业务概览（标签上、数字下）；end：高级指标（标题左、数字右） */
    valuePlacement?: 'stack' | 'end';
  }>(),
  {
    hint: '',
    valuePlacement: 'stack'
  }
);
</script>
