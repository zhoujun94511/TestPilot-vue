<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { cn } from '@/lib/utils';

const props = defineProps<{ class?: HTMLAttributes['class'] }>();
</script>

<template>
  <header :class="cn('flex flex-col gap-1.5 p-5 pb-0', props.class)">
    <slot />
  </header>
</template>
