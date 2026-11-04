/** 列表请求场景：控制 BaseTable loading 与顶栏刷新按钮，避免翻页时整表/工具栏闪动 */

export type ListFetchMode = 'initial' | 'page' | 'refresh' | 'filter';

export function shouldShowTableLoading(hasRows: boolean, mode: ListFetchMode): boolean {
  if (mode === 'page') return false;
  if (!hasRows || mode === 'initial') return true;
  return mode === 'filter' || mode === 'refresh';
}
