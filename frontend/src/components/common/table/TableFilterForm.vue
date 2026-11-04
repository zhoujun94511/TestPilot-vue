<script setup lang="ts">
import { tableFilterFormClass } from '@/lib/table-ui';

defineEmits<{
  (event: 'submit'): void;
}>();
</script>

<template>
  <form :class="tableFilterFormClass" novalidate @submit.prevent="$emit('submit')">
    <slot />
  </form>
</template>
