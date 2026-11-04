<template>
  <Card
    :class="
      cn(
        surfacePanelClass,
        props.class
      )
    "
  >
    <CardHeader v-if="$slots.header || title || subtitle">
      <slot name="header">
        <div v-if="title || subtitle">
          <div :class="sectionTitleClass">{{ title }}</div>
          <div v-if="subtitle" :class="cardSubtitleClass">{{ subtitle }}</div>
        </div>
      </slot>
    </CardHeader>

    <CardContent :class="{ '!pt-0': !padded && !$slots.header && !title && !subtitle }">
      <slot />
    </CardContent>

    <CardFooter v-if="$slots.footer">
      <slot name="footer" />
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { cardSubtitleClass, sectionTitleClass } from '@/lib/page-typography';
import { surfacePanelClass } from '@/lib/surface-ui';
import { cn } from '@/lib/utils';

const props = withDefaults(defineProps<{
  title?: string;
  subtitle?: string;
  padded?: boolean;
  class?: HTMLAttributes['class'];
}>(), {
  padded: true
});
</script>
