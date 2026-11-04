<template>
  <div v-if="text" :class="cn(variant === 'meta' ? tableToolbarMetaLine() : tableToolbarSubtitle(), props.class)">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { cn } from '@/lib/utils';
import { formatListPaginationSummary, type PaginationLike } from '@/lib/pagination-ui';
import { tableToolbarMetaLine, tableToolbarSubtitle } from '@/lib/table-ui';

const props = withDefaults(
  defineProps<{
    pagination: PaginationLike;
    /** subtitle：紧挨标题；meta：在业务副标题之下 */
    variant?: 'subtitle' | 'meta';
    class?: string;
  }>(),
  {
    variant: 'subtitle'
  }
);

const { t } = useI18n();

const text = computed(() =>
  formatListPaginationSummary(props.pagination, (key, params) => t(key, params))
);
</script>
