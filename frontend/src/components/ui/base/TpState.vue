<template>
  <section :class="rootClass">
    <div
      v-if="showSpinner"
      class="mx-auto mb-3 size-8 animate-spin rounded-full border-[3px] border-primary/20 border-t-primary"
      aria-hidden="true"
    />
    <div :class="titleClass">{{ title }}</div>
    <div
      v-if="message"
      :class="
        cn('mt-1.5 text-sm leading-relaxed [overflow-wrap:anywhere]', {
          'text-[var(--tp-color-text-700)]': variant === 'error' || variant === 'warning',
          'text-muted-foreground': variant !== 'error' && variant !== 'warning'
        })
      "
    >
      {{ message }}
    </div>
    <div v-if="$slots.default" class="mt-2">
      <slot />
    </div>
    <div v-if="$slots.actions" class="mt-3.5 flex flex-wrap justify-center gap-2.5">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/lib/utils';

type Variant = 'loading' | 'empty' | 'error' | 'success' | 'warning' | 'info' | 'processing' | 'analyzing' | 'generating';

const props = defineProps<{
  variant: Variant;
  title: string;
  message?: string;
}>();

const rootClass = computed(() => cn('px-5 py-7 text-center text-foreground'));

const titleClass = computed(() =>
  cn('text-base font-bold leading-tight text-foreground', {
    'text-[var(--tp-color-danger-600)]': props.variant === 'error',
    'text-[var(--tp-color-warning-600)]': props.variant === 'warning'
  })
);

const showSpinner = computed(() => ['loading', 'processing', 'analyzing', 'generating'].includes(props.variant));
</script>
