<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { computed } from 'vue';
import { cn } from '@/lib/utils';
import { inputVariants, mergeControlSizeClass } from '@/lib/field-control';
import { tableFilterInputWidth } from '@/lib/table-ui';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    type?: string;
    placeholder?: string;
    ariaLabel?: string;
    disabled?: boolean;
    class?: HTMLAttributes['class'];
  }>(),
  {
    type: 'search'
  }
);

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'keyup', payload: KeyboardEvent): void;
}>();

const classes = computed(() =>
  mergeControlSizeClass(inputVariants(), tableFilterInputWidth(), props.class)
);
</script>

<template>
  <input
    :type="type"
    :class="classes"
    :value="modelValue"
    :placeholder="placeholder"
    :aria-label="ariaLabel"
    :disabled="disabled"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    @keyup="emit('keyup', $event)"
  />
</template>
