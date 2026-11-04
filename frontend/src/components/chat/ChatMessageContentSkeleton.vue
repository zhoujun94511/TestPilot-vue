<template>
  <div class="chat-content-skeleton" :class="`chat-content-skeleton--${variant}`">
    <div
      v-for="(width, index) in lineWidths"
      :key="index"
      class="chat-content-skeleton__line"
      :style="{ width }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  role?: 'user' | 'assistant' | 'system';
  content?: string;
}>(), {
  role: 'assistant',
  content: ''
});

const variant = computed(() => {
  if (props.role === 'user') return 'user';
  if (props.role === 'system') return 'system';
  return 'assistant';
});

const lineWidths = computed(() => {
  const length = String(props.content || '').length;
  const lineCount = Math.min(6, Math.max(2, Math.ceil(length / 80)));
  const defaults = variant.value === 'user'
    ? ['58%', '52%', '46%', '42%', '38%', '34%']
    : variant.value === 'system'
      ? ['80%', '74%', '68%', '62%', '56%', '50%']
      : ['92%', '86%', '78%', '72%', '66%', '60%'];
  return defaults.slice(0, lineCount);
});
</script>
