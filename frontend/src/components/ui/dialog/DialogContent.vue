<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { cn } from '@/lib/utils';

const props = defineProps<{
  class?: HTMLAttributes['class'];
  labelledBy?: string;
}>();
</script>

<template>
  <div
    role="dialog"
    aria-modal="true"
    :aria-labelledby="labelledBy"
    :class="
      cn(
        'relative z-[1051] flex w-full max-w-lg flex-col gap-6 rounded-lg border border-[var(--tp-border-strong)] bg-[var(--tp-bg-surface)] p-6 text-foreground shadow-[var(--tp-shadow-lg)]',
        props.class
      )
    "
    @click.stop
  >
    <slot />
  </div>
</template>
