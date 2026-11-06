<template>
  <div :class="tableBlockRoot()">
    <div v-if="$slots.toolbar" :class="tableBlockToolbar()">
      <slot name="toolbar" />
    </div>

    <BaseState v-if="showBlockingLoading" variant="loading" :title="loadingTitle" :message="loadingMessage" />

    <BaseState
      v-else-if="loadFailed"
      variant="error"
      :title="errorEmptyTitle || emptyTitle"
      :message="emptyMessage"
      :retry-text="retryText"
      @retry="emit('retry')"
    />

    <BaseState v-else-if="!data.length && !showPreservedLoading" variant="empty" :title="emptyTitle" :message="emptyMessage" />

    <template v-else-if="data.length || showPreservedLoading">
      <div class="relative min-h-[8rem] min-w-0" :aria-busy="showPreservedLoading || undefined">
        <div
          v-if="showPreservedLoading"
          class="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center rounded-[var(--tp-radius-md)] bg-[color-mix(in_srgb,var(--tp-bg-surface)_72%,transparent)]"
        >
          <span class="text-sm font-medium text-[var(--tp-color-text-600)]">{{ loadingTitle }}</span>
        </div>
        <div :class="cn(tableWrap(), scrollable && tableBodyScrollClass, showPreservedLoading && 'opacity-55')">
        <table :class="tableElement()" :style="tableMinStyle">
          <thead>
            <tr>
              <th v-if="selectable" :class="tableHeadCell()" :style="selectColStyle">
                <input
                  :class="tableCheckboxClass"
                  type="checkbox"
                  :checked="allSelected"
                  :disabled="!data.length"
                  @change="toggleAll(($event.target as HTMLInputElement).checked)"
                />
              </th>
              <th
                v-for="column in columns"
                :key="column.key"
                :style="columnLayoutStyle(column)"
                :class="cn(tableHeadCell(), column.headerClass)"
              >
                {{ column.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in data"
              :key="resolveRowKey(row)"
              :class="resolveRowClass(row)"
              @click="emit('rowClick', row)"
            >
              <td v-if="selectable" :class="tableBodyCell()" :style="selectColStyle">
                <input
                  :class="tableCheckboxClass"
                  type="checkbox"
                  :checked="selectedKeys.includes(resolveRowKey(row))"
                  @change="toggleRow(resolveRowKey(row), ($event.target as HTMLInputElement).checked)"
                  @click.stop
                />
              </td>
              <td
                v-for="column in columns"
                :key="column.key"
                :style="columnLayoutStyle(column)"
                :class="cn(tableBodyCell(), column.cellClass)"
              >
                <slot
                  :name="`cell-${column.key}`"
                  :row="row"
                  :column="column"
                  :value="getCellValue(row, column.key)"
                >
                  {{ renderCellValue(row, column.key) }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </template>

    <div v-if="$slots.footer" :class="tableBlockFooter()">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { computed } from 'vue';
import { cn } from '@/lib/utils';
import {
  tableBlockFooter,
  tableBlockRoot,
  tableBlockToolbar,
  tableBodyCell,
  tableBodyRow,
  tableCheckboxClass,
  tableElement,
  tableHeadCell,
  tableRowSelected,
  tableWrap,
  tableBodyScrollClass
} from '@/lib/table-ui';
import BaseState from './BaseState.vue';

export interface BaseTableColumn {
  key: string;
  label: string;
  width?: string;
  headerClass?: string;
  cellClass?: string;
}

const props = defineProps<{
  columns: BaseTableColumn[];
  data: T[];
  loading?: boolean;
  loadingTitle: string;
  loadingMessage?: string;
  emptyTitle: string;
  emptyMessage?: string;
  /** 加载失败且无数据时（emptyMessage 有值）使用的标题，避免误显示「暂无数据」 */
  errorEmptyTitle?: string;
  retryText?: string;
  selectable?: boolean;
  selectedKeys?: Array<string | number>;
  rowKey?: string | ((row: T) => string | number);
  rowClass?: (row: T) => string | string[] | Record<string, boolean> | undefined;
  /** 为 true 时全选仅 emit toggleAll，由父组件异步更新 selectedKeys（跨页全选） */
  managedSelectAll?: boolean;
  /** 为 true 且已有 data 时：保留表格与分页，仅加半透明遮罩（避免翻页顶栏闪动） */
  keepContentWhileLoading?: boolean;
  /** 行数较多时限制表格高度，在表体内滚动而不是把页面撑长 */
  scrollable?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:selectedKeys', value: Array<string | number>): void;
  (event: 'rowClick', row: T): void;
  (event: 'toggleAll', value: boolean): void;
  (event: 'retry'): void;
}>();

const showPreservedLoading = computed(
  () => Boolean(props.loading && props.keepContentWhileLoading && props.data.length > 0)
);

const showBlockingLoading = computed(
  () => Boolean(props.loading && !showPreservedLoading.value)
);

const loadFailed = computed(
  () => !props.loading && props.data.length === 0 && Boolean(props.emptyMessage?.trim())
);

/** 未声明列宽时的窄屏底线，避免标题列被压成一字宽 */
const NARROW_FALLBACK_COL = '10rem';
const selectColStyle = { width: '44px', '--tp-col': '44px' };

function columnLayoutStyle(column: BaseTableColumn) {
  const width = column.width || NARROW_FALLBACK_COL;
  return {
    ...(column.width ? { width: column.width } : {}),
    '--tp-col': width
  };
}

const tableMinStyle = computed(() => {
  const parts = props.columns.map((column) => column.width || NARROW_FALLBACK_COL);
  if (props.selectable) parts.unshift('44px');
  return { '--tp-table-min': `calc(${parts.join(' + ')})` };
});

const selectedKeys = computed(() => props.selectedKeys || []);
const allSelected = computed(() => props.selectable && props.data.length > 0 && props.data.every((row) => selectedKeys.value.includes(resolveRowKey(row))));

function resolveRowKey(row: T) {
  if (typeof props.rowKey === 'function') {
    return props.rowKey(row);
  }
  if (props.rowKey) {
    const value = row[props.rowKey];
    return (value ?? '') as string | number;
  }
  return (row.id ?? JSON.stringify(row)) as string | number;
}

function resolveRowClass(row: T) {
  const customClass = props.rowClass ? props.rowClass(row) : undefined;
  const selected = selectedKeys.value.includes(resolveRowKey(row));
  return cn(tableBodyRow(), selected && tableRowSelected(), customClass);
}

function getCellValue(row: T, key: string) {
  return row[key];
}

function renderCellValue(row: T, key: string) {
  const value = getCellValue(row, key);
  if (value === null || value === undefined) return '-';
  return String(value);
}

function toggleRow(key: string | number, checked: boolean) {
  const next = new Set(selectedKeys.value);
  if (checked) next.add(key);
  else next.delete(key);
  emit('update:selectedKeys', Array.from(next));
}

function toggleAll(checked: boolean) {
  emit('toggleAll', checked);
  if (props.managedSelectAll) return;
  const pageKeys = props.data.map((row) => resolveRowKey(row));
  if (!checked) {
    const pageKeySet = new Set(pageKeys.map((key) => String(key)));
    const selectedOutsidePage = selectedKeys.value.some((key) => !pageKeySet.has(String(key)));
    if (selectedOutsidePage) {
      emit('update:selectedKeys', []);
      return;
    }
  }
  const next = new Set(selectedKeys.value);
  if (checked) pageKeys.forEach((key) => next.add(key));
  else pageKeys.forEach((key) => next.delete(key));
  emit('update:selectedKeys', Array.from(next));
}
</script>
