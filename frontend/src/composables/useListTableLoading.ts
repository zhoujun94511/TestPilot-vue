import { ref, type Ref } from 'vue';
import { shouldShowTableLoading, type ListFetchMode } from '@/lib/list-fetch-mode';

/** 列表页 BaseTable loading / refresh 与 list-fetch-mode 对齐 */
export function useListTableLoading<T>(
  rows: Ref<T[]>,
  options?: { refreshLoading?: Ref<boolean> }
) {
  const listLoading = ref(false);
  const listError = ref('');

  function beginLoad(mode: ListFetchMode) {
    listError.value = '';
    if (mode === 'refresh' && options?.refreshLoading) {
      options.refreshLoading.value = true;
    }
    listLoading.value = shouldShowTableLoading(rows.value.length > 0, mode);
  }

  function endLoad() {
    listLoading.value = false;
    if (options?.refreshLoading) {
      options.refreshLoading.value = false;
    }
  }

  function failLoad(message: string, onClearRows?: () => void) {
    listError.value = message;
    onClearRows?.();
  }

  return {
    listLoading,
    listError,
    beginLoad,
    endLoad,
    failLoad
  };
}
