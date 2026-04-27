<template>
  <div>
    <BaseState v-if="loading" variant="loading" :title="loadingTitle" :message="loadingMessage" />

    <BaseState v-else-if="!data.length" variant="empty" :title="emptyTitle" :message="emptyMessage" />

    <template v-else>
      <div class="tp-table-wrap">
        <table class="tp-table">
          <thead>
            <tr>
              <th v-if="selectable" style="width: 44px">
                <input
                  class="tp-check"
                  type="checkbox"
                  :checked="allSelected"
                  :disabled="!data.length"
                  @change="toggleAll(($event.target as HTMLInputElement).checked)"
                />
              </th>
              <th
                v-for="column in columns"
                :key="column.key"
                :style="column.width ? { width: column.width } : undefined"
                :class="column.headerClass"
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
              <td v-if="selectable">
                <input
                  class="tp-check"
                  type="checkbox"
                  :checked="selectedKeys.includes(resolveRowKey(row))"
                  @change="toggleRow(resolveRowKey(row), ($event.target as HTMLInputElement).checked)"
                  @click.stop
                />
              </td>
              <td
                v-for="column in columns"
                :key="column.key"
                :class="column.cellClass"
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
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
  data: Record<string, unknown>[];
  loading?: boolean;
  loadingTitle: string;
  loadingMessage?: string;
  emptyTitle: string;
  emptyMessage?: string;
  selectable?: boolean;
  selectedKeys?: Array<string | number>;
  rowKey?: string | ((row: Record<string, unknown>) => string | number);
  rowClass?: (row: Record<string, unknown>) => string | string[] | Record<string, boolean> | undefined;
}>();

const emit = defineEmits<{
  (event: 'update:selectedKeys', value: Array<string | number>): void;
  (event: 'rowClick', row: Record<string, unknown>): void;
  (event: 'toggleAll', value: boolean): void;
}>();

const selectedKeys = computed(() => props.selectedKeys || []);
const allSelected = computed(() => props.selectable && props.data.length > 0 && props.data.every((row) => selectedKeys.value.includes(resolveRowKey(row))));

function resolveRowKey(row: Record<string, unknown>) {
  if (typeof props.rowKey === 'function') {
    return props.rowKey(row);
  }
  if (props.rowKey) {
    return row[props.rowKey] as string | number;
  }
  return (row.id ?? JSON.stringify(row)) as string | number;
}

function resolveRowClass(row: Record<string, unknown>) {
  const customClass = props.rowClass ? props.rowClass(row) : undefined;
  return [
    { 'tp-table-row--selected': selectedKeys.value.includes(resolveRowKey(row)) },
    customClass
  ];
}

function getCellValue(row: Record<string, unknown>, key: string) {
  return row[key];
}

function renderCellValue(row: Record<string, unknown>, key: string) {
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
  emit('update:selectedKeys', checked ? props.data.map((row) => resolveRowKey(row)) : []);
}
</script>
