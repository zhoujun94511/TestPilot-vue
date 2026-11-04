<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { computed } from 'vue';
import { cn } from '@/lib/utils';
import { mergeControlSizeClass, selectVariants } from '@/lib/field-control';
import { tableFilterSelectWidth } from '@/lib/table-ui';

const props = defineProps<{
  modelValue: string;
  disabled?: boolean;
  class?: HTMLAttributes['class'];
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'change', value: string): void;
}>();

const classes = computed(() =>
  mergeControlSizeClass(selectVariants(), tableFilterSelectWidth(), props.class)
);

function onChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  emit('update:modelValue', value);
  emit('change', value);
}
</script>

<template>
  <select :class="classes" :value="modelValue" :disabled="disabled" @change="onChange">
    <slot />
  </select>
</template>
