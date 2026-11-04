<template>
  <div>
    <div
      class="h-2.5 w-full overflow-hidden rounded-full bg-muted"
      role="progressbar"
      :aria-valuenow="normalized"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        :class="barClass"
        class="h-full rounded-full transition-[width] duration-200 ease-out"
        :style="{ width: `${normalized}%` }"
      />
    </div>
    <div v-if="label || showValue" class="mt-1.5 flex justify-between text-xs text-muted-foreground">
      <span>{{ label }}</span>
      <span v-if="showValue">{{ normalized }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/lib/utils';

const props = withDefaults(defineProps<{
  value: number;
  label?: string;
  showValue?: boolean;
  /** primary：通用；ai：与旧版 progress 及 AI 卡片一致 */
  tone?: 'primary' | 'ai';
}>(), {
  showValue: true,
  tone: 'ai'
});

const normalized = computed(() => {
  if (Number.isNaN(props.value)) return 0;
  return Math.max(0, Math.min(100, Math.round(props.value)));
});

const barClass = computed(() =>
  cn({
    'bg-primary': props.tone === 'primary',
    'bg-[var(--tp-color-ai-600)]': props.tone === 'ai'
  })
);
</script>
