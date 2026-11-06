import type { Ref } from 'vue';
import type { ListFetchMode } from '@/lib/list-fetch-mode';
import type { PaginationLike } from '@/lib/pagination-ui';
import { useListTableLoading } from '@/composables/useListTableLoading';
import i18n from '@/i18n';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

export type PaginatedFetchResult<TRow> = {
  rows: TRow[];
  pagination: PaginationLike;
};

export interface FilledListPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export function emptyListPagination(perPage = 10, page = 1): FilledListPagination {
  return {
    page,
    per_page: perPage,
    total: 0,
    pages: 0,
    has_prev: false,
    has_next: false
  };
}

type LoadFailOptions = {
  resolveMessage: (error: unknown) => string;
  onClear?: () => void;
};

/**
 * 列表分页请求：包装 useListTableLoading + 统一的 rows/pagination 赋值与错误处理。
 * 各页 filter、选中态、路由副作用仍在 loadXxx 内完成。
 */
export function usePaginatedList<TRow>(
  rows: Ref<TRow[]>,
  options?: {
    refreshLoading?: Ref<boolean>;
    pagination?: Ref<PaginationLike>;
  }
) {
  const loading = useListTableLoading(rows, { refreshLoading: options?.refreshLoading });
  let requestSeq = 0;

  /** 连续翻页或改筛选时，只有最后一次请求的结果会写入列表 */
  async function loadPage(
    page: number,
    mode: ListFetchMode,
    fetcher: () => Promise<PaginatedFetchResult<TRow>>,
    fail?: LoadFailOptions
  ): Promise<PaginatedFetchResult<TRow> | undefined> {
    const seq = ++requestSeq;
    loading.beginLoad(mode);
    try {
      const result = await fetcher();
      if (seq !== requestSeq) return undefined;
      rows.value = result.rows;
      if (options?.pagination) {
        options.pagination.value = result.pagination;
      }
      return result;
    } catch (error) {
      if (seq !== requestSeq) return undefined;
      if (fail) {
        loading.failLoad(fail.resolveMessage(error), fail.onClear);
      } else {
        loading.failLoad(getUserFacingErrorMessage(error, String(i18n.global.t('common.errors.requestFailed'))));
      }
      return undefined;
    } finally {
      if (seq === requestSeq) loading.endLoad();
    }
  }

  return {
    listLoading: loading.listLoading,
    listError: loading.listError,
    beginLoad: loading.beginLoad,
    endLoad: loading.endLoad,
    failLoad: loading.failLoad,
    loadPage
  };
}
