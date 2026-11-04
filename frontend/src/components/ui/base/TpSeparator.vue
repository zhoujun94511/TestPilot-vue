<template>
  <Separator :orientation="orientation" />
</template>

<script setup lang="ts">
import { Separator } from '@/components/ui/separator';

withDefaults(
  defineProps<{
    orientation?: 'horizontal' | 'vertical';
  }>(),
  {
    orientation: 'horizontal'
  }
);
</script>
