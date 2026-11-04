import { cn } from '@/lib/utils';

/** PageNoticeBanner 根节点标记（调试 / 测试钩子） */
export const PAGE_NOTICE_BANNER_MARKER = 'page-notice-banner';

/**
 * 页面级工具栏、表单底栏（ActionBar / 生成表单等）
 *
 * ActionBar / PagePanel #actions：操作组包在 `pageToolbarStripClass` 内；ghost sm + primary sm（Chat、Config、列表页一致）。
 */

export const pageToolbarClass =
  'mb-[var(--tp-space-3)] flex flex-wrap items-start justify-between gap-[var(--tp-space-3)]';

/** 仅 #actions、无 lead 时避免空 flex-1 把按钮顶到右侧「孤岛」 */
export const pageToolbarActionsOnlyClass =
  'mb-[var(--tp-space-3)] flex flex-wrap items-center justify-end gap-2.5 max-[1199px]:flex-wrap min-[1200px]:flex-nowrap';

export const pageToolbarLeadClass =
  'flex min-w-0 flex-1 items-center';

export const pageToolbarSubtitleClass =
  'mb-0 max-w-[72ch] text-sm text-muted-foreground';

export const toolbarActionsClass =
  'flex flex-wrap items-center justify-end gap-2.5 max-[1199px]:flex-wrap min-[1200px]:flex-nowrap';

/** ActionBar 内多簇操作（列表区 | 生成/导出区） */
export const toolbarActionClusterClass = 'flex flex-wrap items-center justify-end gap-2';

export const toolbarActionClusterDividerClass =
  'hidden h-6 w-px shrink-0 bg-[var(--tp-border-default)] min-[900px]:block';

/** @deprecated 改用 pageToolbarStripClass + ToolbarOverflowMenu */
export const toolbarActionStackClass =
  'flex w-full max-w-full flex-col items-end gap-3 min-[900px]:flex-row min-[900px]:items-center min-[900px]:justify-end';

/**
 * PagePanel 顶栏操作条：整组统一外框，内部控件不再各自加边框/底纹。
 * 次要 → TpButton ghost sm；主操作 → primary sm；溢出 → ToolbarOverflowMenu（ghost ⋯）。
 */
export const pageToolbarStripClass = cn(
  'flex max-w-full min-h-[2.375rem] flex-wrap items-center justify-end gap-1',
  'rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-1'
);

/** 顶栏内联开关（如 RAG），仅布局，不加单独外框 */
export const toolbarInlineSwitchClass =
  'flex max-w-[min(100%,280px)] shrink items-center px-1.5 py-0.5';

/** @deprecated 改用 DropdownMenuItem */
export const toolbarOverflowMenuItemClass =
  'flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm';

/** @deprecated */
export const toolbarOverflowMenuSectionClass = 'px-2 py-1.5';

export const toolbarBulkBarClass = cn(
  'mb-3 flex flex-wrap items-center justify-between gap-3 rounded-[var(--tp-radius-md)]',
  'border border-[color-mix(in_srgb,var(--tp-color-primary-600)_22%,var(--tp-border-default))]',
  'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_8%,var(--tp-bg-surface))] px-3 py-2'
);

export const toolbarBulkBarMetaClass = 'text-sm font-semibold text-[var(--tp-color-text-700)]';

export const formActionsClass =
  'mt-[var(--tp-space-4)] flex flex-wrap justify-end gap-[var(--tp-space-2)] border-t border-[var(--tp-border-default)] pt-[var(--tp-space-3)]';

/** 常用 flex 行（替代 utilities 中 `.tp-flex` 组合） */
export const flexBetweenStartGap2Class = 'flex items-start justify-between gap-2';

export const flexWrapBetweenStartGap3Class =
  'flex flex-wrap items-start justify-between gap-3';

export const flexWrapEndGap2Class = 'flex flex-wrap items-center justify-end gap-2';

export const flexStartGap3Class = 'flex items-start gap-3';

export const flexGrowMinClass = 'min-w-0 flex-1';

export const flexBetweenCenterGap2Class = 'flex items-center justify-between gap-2';

export const flexCenterGap2Class = 'flex items-center gap-2';
