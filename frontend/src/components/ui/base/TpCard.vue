<template>
  <section class="tp-card" :class="cardClass">
    <header v-if="$slots.header || title || subtitle" class="tp-card__header">
      <slot name="header">
        <div v-if="title || subtitle">
          <div class="tp-card__title">{{ title }}</div>
          <div v-if="subtitle" class="tp-card__subtitle">{{ subtitle }}</div>
        </div>
      </slot>
    </header>

    <div class="tp-card__body">
      <slot />
    </div>

    <footer v-if="$slots.footer" class="tp-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  title?: string;
  subtitle?: string;
  padded?: boolean;
}>(), {
  padded: true
});

const cardClass = computed(() => ({
  'tp-card--flat': !props.padded
}));
</script>

<style scoped>
.tp-card--flat .tp-card__body {
  padding-top: 0;
}
</style>
