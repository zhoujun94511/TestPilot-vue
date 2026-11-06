<template>
  <span class="tp-spinner" :style="boxStyle" aria-hidden="true">
    <svg viewBox="0 0 16 16" fill="none" class="tp-spinner__glyph" :style="boxStyle">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" opacity="0.28" />
      <circle
        cx="8"
        cy="8"
        r="6"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-dasharray="16 22"
      />
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' });

const boxStyle = computed(() => {
  const px = props.size === 'md' ? 16 : 14;
  return { width: `${px}px`, height: `${px}px` };
});
</script>

<style scoped>
/*
 * 转的是这个正方形盒子，不转 svg。svg 用 CSS 旋转时圆心会偏。
 * 宽高写死在元素上：本项目关掉了 preflight，flex 子项的默认 min-height 会让 svg 撑到 150px，按钮就被顶歪。
 */
.tp-spinner {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  line-height: 0;
  vertical-align: middle;
  animation: tp-spinner-rotate 0.7s linear infinite;
}

.tp-spinner__glyph {
  display: block;
  flex: none;
  min-width: 0;
  min-height: 0;
  max-width: none;
}

@keyframes tp-spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
