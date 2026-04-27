<template>
  <section class="tp-state" :class="stateClass">
    <div v-if="showSpinner" class="tp-state__spinner" aria-hidden="true"></div>
    <div class="tp-state__title" :class="titleClass">{{ title }}</div>
    <div v-if="message" class="tp-state__body">{{ message }}</div>
    <div v-if="$slots.default" class="tp-state__content">
      <slot />
    </div>
    <div v-if="$slots.actions" class="tp-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Variant = 'loading' | 'empty' | 'error' | 'success' | 'warning' | 'info' | 'processing' | 'analyzing' | 'generating';

const props = defineProps<{
  variant: Variant;
  title: string;
  message?: string;
}>();

const stateClass = computed(() => ({
  'tp-state--loading': props.variant === 'loading',
  'tp-state--empty': props.variant === 'empty',
  'tp-state--error': props.variant === 'error',
  'tp-state--success': props.variant === 'success',
  'tp-state--warning': props.variant === 'warning',
  'tp-state--info': props.variant === 'info',
  'tp-state--processing': props.variant === 'processing',
  'tp-state--analyzing': props.variant === 'analyzing',
  'tp-state--generating': props.variant === 'generating'
}));

const titleClass = computed(() => ({
  'tp-state__title--danger': props.variant === 'error',
  'tp-state__title--warning': props.variant === 'warning'
}));

const showSpinner = computed(() => ['loading', 'processing', 'analyzing', 'generating'].includes(props.variant));
</script>
