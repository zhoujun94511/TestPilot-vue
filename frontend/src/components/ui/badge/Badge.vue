<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex shrink-0 items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        neutral: 'border-border bg-muted text-muted-foreground',
        default: 'border-transparent bg-primary/15 text-[var(--tp-color-primary-700)]',
        primary: 'border-transparent bg-primary/15 text-[var(--tp-color-primary-700)]',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        ai: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-ai-600)_14%,var(--tp-bg-surface))] text-[var(--tp-color-ai-600)]',
        success: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-success-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-success-600)]',
        warning: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-warning-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-warning-600)]',
        destructive: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-danger-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-danger-600)]',
        danger: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-danger-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-danger-600)]',
        outline: 'text-foreground border-border',
        info: 'border-transparent bg-[color-mix(in_srgb,var(--tp-color-info-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-info-600)]'
      }
    },
    defaultVariants: {
      variant: 'neutral'
    }
  }
);

type BadgeVariants = VariantProps<typeof badgeVariants>;

const props = withDefaults(
  defineProps<{
    variant?: NonNullable<BadgeVariants['variant']>;
    class?: HTMLAttributes['class'];
  }>(),
  {
    variant: 'neutral'
  }
);

const classes = computed(() => cn(badgeVariants({ variant: props.variant }), props.class));
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
