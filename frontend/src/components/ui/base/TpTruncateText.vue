<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { TooltipContent, TooltipPortal, TooltipRoot, TooltipTrigger } from 'reka-ui';
import { tooltipContentClass } from '@/lib/tooltip-ui';
import { cn } from '@/lib/utils';

const props = withDefaults(
  defineProps<{
    text: string;
    class?: HTMLAttributes['class'];
    side?: 'top' | 'right' | 'bottom' | 'left';
  }>(),
  { side: 'top' }
);
</script>

<template>
  <TooltipRoot v-if="text.trim()" :delay-duration="400">
    <TooltipTrigger as-child>
      <span :class="cn('block min-w-0 truncate', props.class)">{{ text }}</span>
    </TooltipTrigger>
    <TooltipPortal>
      <TooltipContent :class="tooltipContentClass" :side="side" :side-offset="6">
        {{ text }}
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
  <span v-else :class="cn('block min-w-0 truncate', props.class)" />
</template>
