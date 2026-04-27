<template>
  <div>
    <div class="tp-progress" role="progressbar" :aria-valuenow="normalized" aria-valuemin="0" aria-valuemax="100">
      <div class="tp-progress__bar" :style="{ width: `${normalized}%` }"></div>
    </div>
    <div v-if="label || showValue" class="tp-progress__meta">
      <span>{{ label }}</span>
      <span v-if="showValue">{{ normalized }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  value: number;
  label?: string;
  showValue?: boolean;
}>(), {
  showValue: true
});

const normalized = computed(() => {
  if (Number.isNaN(props.value)) return 0;
  return Math.max(0, Math.min(100, Math.round(props.value)));
});
</script>
