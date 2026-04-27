<template>
  <div class="tp-page-title">
    <div class="min-w-0">
      <slot name="title">
        <h1 class="tp-page-title__heading">{{ title }}</h1>
      </slot>
      <slot name="subtitle">
        <p v-if="subtitle" class="tp-page-title__subtitle tp-mb-0">{{ subtitle }}</p>
      </slot>
    </div>

    <div class="tp-toolbar__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  subtitle?: string;
}>();
</script>
