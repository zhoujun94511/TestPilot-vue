import type { Ref } from 'vue';
import type { ListFetchMode } from '@/lib/list-fetch-mode';
import type { PaginationLike } from '@/lib/pagination-ui';

/** ListTablePager @change：校验页码后触发 load(page, 'page') */
export function useListPageChange(
  pagination: Ref<PaginationLike>,
  loadPage: (page: number, mode: ListFetchMode) => void | Promise<void>,
  options?: {
    /** 同步 filters.page 等本地状态 */
    onAcceptPage?: (page: number) => void;
  }
) {
  async function changePage(page: number) {
    const maxPages = Math.max(1, Number(pagination.value.pages || 1));
    if (page < 1 || page > maxPages) return;
    options?.onAcceptPage?.(page);
    await loadPage(page, 'page');
  }

  return { changePage };
}
