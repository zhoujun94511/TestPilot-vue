<template>
  <BaseTable
    scrollable
    :columns="columns"
    :data="pageRows"
    :loading="loading"
    :loading-title="loadingTitle"
    :empty-title="emptyTitle"
    :empty-message="emptyMessage"
    :row-key="rowKey"
  >
    <template #toolbar>
      <TableToolbar :title="title" :pagination="pagination">
        <template v-if="$slots.actions" #actions>
          <slot name="actions" />
        </template>
      </TableToolbar>
    </template>
    <template #footer>
      <ListTablePager :pagination="pagination" :loading="loading" @change="changePage" />
    </template>
  </BaseTable>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ListTablePager from '@/components/common/ListTablePager.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import type { PaginationLike } from '@/lib/pagination-ui';

const props = withDefaults(
  defineProps<{
    title: string;
    columns: BaseTableColumn[];
    rows: Record<string, unknown>[];
    rowKey: string;
    emptyTitle: string;
    emptyMessage?: string;
    loading?: boolean;
    loadingTitle?: string;
    perPage?: number;
  }>(),
  {
    emptyMessage: '',
    loading: false,
    loadingTitle: '',
    perPage: 10
  }
);

const page = ref(1);

watch(
  () => props.rows,
  () => {
    page.value = 1;
  }
);

const pagination = computed<PaginationLike>(() => {
  const total = props.rows.length;
  const perPage = Math.max(1, props.perPage);
  const pages = Math.max(1, Math.ceil(total / perPage) || 1);
  const current = Math.min(Math.max(1, page.value), pages);
  return {
    page: current,
    per_page: perPage,
    total,
    pages: total > 0 ? pages : 0,
    has_prev: current > 1,
    has_next: current < pages
  };
});

const pageRows = computed(() => {
  const current = Number(pagination.value.page ?? 1);
  const perPage = Number(pagination.value.per_page ?? props.perPage);
  const start = (current - 1) * perPage;
  return props.rows.slice(start, start + perPage);
});

function changePage(next: number) {
  const pages = Number(pagination.value.pages ?? 1);
  if (next < 1 || next > pages) return;
  page.value = next;
}
</script>
