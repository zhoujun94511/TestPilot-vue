<template>
  <div :class="cn(tableToolbarRoot(), props.class)">
    <div v-if="$slots.meta || title || subtitle || pagination" :class="tableToolbarMeta()">
      <div v-if="title" :class="tableToolbarTitle()">{{ title }}</div>
      <div v-if="subtitle" :class="tableToolbarSubtitle()">{{ subtitle }}</div>
      <ListPaginationSummary
        v-if="pagination"
        :pagination="pagination"
        :variant="subtitle ? 'meta' : 'subtitle'"
      />
      <div v-if="$slots.meta" :class="tableToolbarMetaLine()">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.filters" :class="tableToolbarFilters()">
      <slot name="filters" />
    </div>
    <div v-if="$slots.actions" :class="tableToolbarActions()">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import ListPaginationSummary from '@/components/common/ListPaginationSummary.vue';
import type { PaginationLike } from '@/lib/pagination-ui';
import { cn } from '@/lib/utils';
import {
  tableToolbarActions,
  tableToolbarFilters,
  tableToolbarMeta,
  tableToolbarMetaLine,
  tableToolbarRoot,
  tableToolbarSubtitle,
  tableToolbarTitle
} from '@/lib/table-ui';

const props = defineProps<{
  title?: string;
  subtitle?: string;
  /** 与 subtitle 二选一或并存（并存时分页摘要在 meta 行） */
  pagination?: PaginationLike;
  class?: HTMLAttributes['class'];
}>();
</script>
