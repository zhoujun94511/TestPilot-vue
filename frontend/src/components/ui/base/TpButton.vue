<template>
  <component
    :is="tag"
    :type="tag === 'button' ? type : undefined"
    :href="href"
    :to="to"
    :class="classes"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading || undefined"
    @click="emit('click', $event)"
  >
    <span
      v-if="loading"
      class="inline-block h-[0.85rem] w-[0.85rem] animate-spin rounded-full border-2 border-current border-r-transparent"
      aria-hidden="true"
    />
    <span v-if="$slots.icon" class="inline-flex shrink-0 items-center justify-center">
      <slot name="icon" />
    </span>
    <span class="inline-flex items-center">
      <slot />
    </span>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost' | 'ai' | 'success' | 'danger' | 'warning';
type Size = 'sm' | 'md';

const tpButtonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md border-0 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring focus-visible:ring-offset-0 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:opacity-90 active:opacity-95',
        secondary:
          'border border-[var(--tp-border-default)] bg-secondary text-secondary-foreground hover:border-[var(--tp-border-strong)] hover:bg-[color-mix(in_srgb,var(--tp-accent)_55%,var(--tp-bg-surface))] active:opacity-95',
        ghost:
          'border border-[color-mix(in_srgb,var(--tp-border-default)_72%,transparent)] bg-transparent hover:border-[var(--tp-border-strong)] hover:bg-accent hover:text-accent-foreground active:bg-[color-mix(in_srgb,var(--tp-accent)_80%,var(--tp-bg-surface))]',
        ai: 'bg-[var(--tp-color-ai-600)] text-white hover:opacity-90',
        success: 'bg-[var(--tp-color-success-600)] text-white hover:opacity-90',
        danger: 'bg-destructive text-destructive-foreground hover:opacity-90',
        warning: 'bg-[var(--tp-color-warning-600)] text-white hover:opacity-90'
      },
      size: {
        md: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs'
      }
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md'
    }
  }
);

type TpButtonVariants = VariantProps<typeof tpButtonVariants>;

const props = withDefaults(defineProps<{
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  href?: string;
  to?: string;
  class?: string;
}>(), {
  variant: 'primary',
  size: 'md',
  type: 'button'
});

const emit = defineEmits<{
  (event: 'click', eventObject: MouseEvent): void;
}>();

const tag = computed(() => (props.href ? 'a' : props.to ? 'router-link' : 'button'));

const classes = computed(() =>
  cn(
    tpButtonVariants({
      variant: props.variant as NonNullable<TpButtonVariants['variant']>,
      size: props.size
    }),
    props.href || props.to ? 'no-underline' : '',
    props.class
  )
);
</script>
