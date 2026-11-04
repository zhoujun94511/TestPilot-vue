<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue';
import { cn } from '@/lib/utils';

const props = withDefaults(
  defineProps<{
    orientation?: 'horizontal' | 'vertical';
    decorative?: boolean;
    class?: HTMLAttributes['class'];
  }>(),
  {
    orientation: 'horizontal',
    decorative: true
  }
);

const classes = computed(() =>
  cn(
    'shrink-0 bg-border',
    props.orientation === 'horizontal' ? 'h-px w-full my-4' : 'h-5 w-px mx-2',
    props.class
  )
);
</script>

<template>
  <div
    :role="decorative ? 'none' : 'separator'"
    :aria-orientation="decorative ? undefined : orientation"
    :class="classes"
  />
</template>
