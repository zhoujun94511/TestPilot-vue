<template>
  <component
    :is="tag"
    :type="tag === 'button' ? type : undefined"
    :href="href"
    :to="to"
    class="tp-btn"
    :class="buttonClass"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading || undefined"
    @click="emit('click', $event)"
  >
    <span v-if="loading" class="tp-btn__spinner" aria-hidden="true"></span>
    <span v-if="$slots.icon" class="tp-btn__icon">
      <slot name="icon" />
    </span>
    <span class="tp-btn__label">
      <slot />
    </span>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Variant = 'primary' | 'secondary' | 'ghost' | 'ai' | 'success' | 'danger' | 'warning';
type Size = 'sm' | 'md';

const props = withDefaults(defineProps<{
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  href?: string;
  to?: string;
}>(), {
  variant: 'primary',
  size: 'md',
  type: 'button'
});

const emit = defineEmits<{
  (event: 'click', eventObject: MouseEvent): void;
}>();

const tag = computed(() => (props.href ? 'a' : props.to ? 'router-link' : 'button'));

const buttonClass = computed(() => [
  `tp-btn--${props.variant}`,
  props.size === 'sm' ? 'tp-btn--sm' : ''
]);
</script>

<style scoped>
.tp-btn__spinner {
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 9999px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: tp-spin 0.8s linear infinite;
}

.tp-btn__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

@keyframes tp-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
