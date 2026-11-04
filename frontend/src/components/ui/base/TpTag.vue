<template>
  <Badge :variant="badgeVariant" :class="props.class">
    <slot>{{ label }}</slot>
  </Badge>
</template>

<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue';
import { Badge } from '@/components/ui/badge';

type Variant = 'neutral' | 'primary' | 'ai' | 'success' | 'warning' | 'danger' | 'info';

const props = withDefaults(defineProps<{
  label?: string;
  variant?: Variant;
  class?: HTMLAttributes['class'];
}>(), {
  variant: 'neutral'
});

const badgeVariant = computed(() => props.variant);
</script>
