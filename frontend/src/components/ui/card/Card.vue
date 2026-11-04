<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { cn } from '@/lib/utils';

const props = defineProps<{
  class?: HTMLAttributes['class'];
}>();
</script>

<template>
  <section :class="cn('flex min-w-0 flex-col text-foreground', props.class)">
    <slot />
  </section>
</template>
