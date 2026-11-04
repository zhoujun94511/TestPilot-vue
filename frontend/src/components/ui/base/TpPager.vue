<template>
  <div
    v-if="visible"
    :class="cn('flex flex-wrap items-center gap-2', showSummary ? 'justify-between' : 'justify-end', props.class)"
  >
    <div v-if="showSummary" class="text-xs text-muted-foreground">{{ text }}</div>
    <div class="flex gap-2">
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
import { useI18n } from 'vue-i18n';
import { formatListPaginationSummary, shouldShowPager } from '@/lib/pagination-ui';
import { cn } from '@/lib/utils';
import TpButton from './TpButton.vue';

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  page: number;
  perPage: number;
  total: number;
  pages: number;
  hasPrev: boolean;
  hasNext: boolean;
  loading?: boolean;
  /** 为 false 时仅展示翻页按钮（列表页 toolbar 已有条数摘要） */
  showSummary?: boolean;
  previousText?: string;
  nextText?: string;
  class?: string;
}>(), {
  loading: false,
  showSummary: true,
  previousText: 'Prev',
  nextText: 'Next'
});

const emit = defineEmits<{
  (event: 'change', page: number): void;
}>();

const { t } = useI18n();

const visible = computed(() =>
  shouldShowPager({
    page: props.page,
    per_page: props.perPage,
    total: props.total,
    pages: props.pages
  })
);

const text = computed(() =>
  formatListPaginationSummary(
    {
      page: props.page,
      per_page: props.perPage,
      total: props.total,
      pages: props.pages
    },
    (key, params) => t(key, params)
  )
);
</script>
