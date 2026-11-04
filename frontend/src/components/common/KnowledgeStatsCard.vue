<template>
  <div :class="statsSummaryMetricClass">
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <div :class="kpiLabelClass">{{ label }}</div>
        <div :class="kpiValueClass">{{ value }}</div>
      </div>
      <div :class="kpiIconClass" aria-hidden="true">
        <BrandMark v-if="icon === brandMarkIconKey" size="xs" decorative />
        <template v-else>{{ icon }}</template>
      </div>
    </div>
    <div>
      <div :class="[kpiHintClass, { invisible: !hint }]">
        {{ hint || '\u00A0' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  kpiHintClass,
  kpiIconClass,
  kpiLabelClass,
  kpiValueClass
} from '@/lib/page-typography';
import { statsSummaryMetricClass } from '@/lib/stats-ui';
import BrandMark from '@/components/brand/BrandMark.vue';
import { brandMarkIconKey } from '@/lib/brand';

defineProps<{
  label: string;
  value: string | number;
  icon?: string;
  hint?: string;
}>();
</script>
