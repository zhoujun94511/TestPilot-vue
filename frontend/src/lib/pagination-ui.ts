export interface PaginationLike {
  page?: number;
  per_page?: number;
  total?: number;
  pages?: number;
  has_prev?: boolean;
  has_next?: boolean;
}

export function paginationRange(pagination: PaginationLike) {
  const total = Math.max(0, Number(pagination.total ?? 0));
  const perPage = Math.max(1, Number(pagination.per_page ?? 10));
  const pages = Math.max(0, Number(pagination.pages ?? 0));
  const page = Math.min(
    Math.max(1, Number(pagination.page ?? 1)),
    Math.max(1, pages || 1)
  );

  if (total <= 0) {
    return { total: 0, page, pages, perPage, start: 0, end: 0 };
  }

  const start = (page - 1) * perPage + 1;
  const end = Math.min(page * perPage, total);
  return { total, page, pages, perPage, start, end };
}

/** 与 TpPager 一致：有数据且超过一页时才展示分页控件 */
export function shouldShowPager(pagination: PaginationLike) {
  const { total, pages } = paginationRange(pagination);
  return total > 0 && pages > 1;
}

type PaginationTranslate = (
  key: 'common.pagination.range',
  params: { start: number; end: number; total: number }
) => string;

/** 列表 TableToolbar / TpPager 共用文案（基于 common.pagination.range） */
export function formatListPaginationSummary(
  pagination: PaginationLike,
  translate: PaginationTranslate
): string {
  const { total, start, end } = paginationRange(pagination);
  if (total <= 0) return '';
  return translate('common.pagination.range', { start, end, total });
}
