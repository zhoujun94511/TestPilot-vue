<template>
  <TpPager
    v-if="show"
    :page="page"
    :per-page="perPage"
    :total="total"
    :pages="pages"
    :has-prev="hasPrev"
    :has-next="hasNext"
    :loading="loading"
    :show-summary="showSummary"
    :previous-text="previousText"
    :next-text="nextText"
    :class="props.class"
    @change="emit('change', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import TpPager from '@/components/ui/base/TpPager.vue';
import { shouldShowPager, type PaginationLike } from '@/lib/pagination-ui';

const props = withDefaults(
  defineProps<{
    pagination: PaginationLike;
    loading?: boolean;
    /** 列表页 TableToolbar 已展示条数摘要时设为 false */
    showSummary?: boolean;
    previousText?: string;
    nextText?: string;
    class?: string;
  }>(),
  {
    loading: false,
    showSummary: false
  }
);

const emit = defineEmits<{
  (event: 'change', page: number): void;
}>();

const { t } = useI18n();

const show = computed(() => shouldShowPager(props.pagination));

const page = computed(() => Number(props.pagination.page ?? 1));
const perPage = computed(() => Number(props.pagination.per_page ?? 10));
const total = computed(() => Number(props.pagination.total ?? 0));
const pages = computed(() => Number(props.pagination.pages ?? 0));
const hasPrev = computed(() => Boolean(props.pagination.has_prev));
const hasNext = computed(() => Boolean(props.pagination.has_next));

const previousText = computed(() => props.previousText ?? t('common.actions.previous'));
const nextText = computed(() => props.nextText ?? t('common.actions.next'));
</script>
