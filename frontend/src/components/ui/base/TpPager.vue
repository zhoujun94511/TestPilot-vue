<template>
  <div v-if="pages > 1" class="tp-pager">
    <div class="tp-small" style="color: var(--tp-color-text-500)">{{ text }}</div>
    <div class="tp-flex tp-gap-2">
      <TpButton
        variant="secondary"
        size="sm"
        :disabled="loading || !hasPrev"
        @click="emit('change', page - 1)"
      >
        {{ previousText }}
      </TpButton>
      <TpButton
        variant="secondary"
        size="sm"
        :disabled="loading || !hasNext"
        @click="emit('change', page + 1)"
      >
        {{ nextText }}
      </TpButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import TpButton from './TpButton.vue';

const props = withDefaults(defineProps<{
  page: number;
  perPage: number;
  total: number;
  pages: number;
  hasPrev: boolean;
  hasNext: boolean;
  loading?: boolean;
  previousText?: string;
  nextText?: string;
}>(), {
  loading: false,
  previousText: 'Prev',
  nextText: 'Next'
});

const emit = defineEmits<{
  (event: 'change', page: number): void;
}>();

const text = computed(() => {
  if (!props.total) return '0 / 0';
  const start = (props.page - 1) * props.perPage + 1;
  const end = Math.min(props.page * props.perPage, props.total);
  return `${start}-${end} / ${props.total}`;
});
</script>

<style scoped>
.tp-pager {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
</style>
