<template>
  <span class="tp-tag" :class="tagClass">
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Variant = 'neutral' | 'primary' | 'ai' | 'success' | 'warning' | 'danger' | 'info';

const props = withDefaults(defineProps<{
  label?: string;
  variant?: Variant;
}>(), {
  variant: 'neutral'
});

const tagClass = computed(() => `tp-tag--${props.variant}`);
</script>
