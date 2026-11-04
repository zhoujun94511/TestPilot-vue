import { cva } from 'class-variance-authority';
import { fieldFocusRingClass } from '@/lib/field-control';
import { cn } from '@/lib/utils';

/** 供页面 :deep() 布局钩子（如 Knowledge 文件列表滚动区） */
export const BASE_TABLE_BLOCK_CLASS = 'base-table-block';
export const BASE_TABLE_WRAP_CLASS = 'base-table-wrap';

/** BaseTable 行内复选框（原生 input，shadcn 风格） */
export const tableCheckboxClass = cn(
  'h-4 w-4 shrink-0 cursor-pointer rounded border border-input bg-background accent-[var(--tp-color-primary-600)] disabled:cursor-not-allowed disabled:opacity-50',
  fieldFocusRingClass
);

export const tableBlockRoot = cva(`${BASE_TABLE_BLOCK_CLASS} flex min-h-0 min-w-0 flex-col gap-3`);

export const tableBlockToolbar = cva('shrink-0');

export const tableBlockFooter = cva('flex shrink-0 justify-end');

export const tableWrap = cva(
  `${BASE_TABLE_WRAP_CLASS} min-w-0 overflow-auto rounded-lg border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] dark:border-[var(--tp-border-strong)] dark:bg-[color-mix(in_srgb,var(--tp-bg-surface)_92%,var(--tp-bg-subtle))]`
);

/** 列表超过一屏时在表格体内滚动，表头 sticky 仍相对该区域 */
export const tableBodyScrollClass =
  'tp-subtle-scrollbar max-h-[min(28rem,52vh)] overscroll-y-contain [scrollbar-width:thin]';

export const tableElement = cva(
  'w-full border-separate border-spacing-0 text-[var(--tp-color-text-900)]'
);

export const tableHeadCell = cva(
  'sticky top-0 z-[1] border-b border-[var(--tp-border-default)] bg-muted px-[14px] py-[11px] text-left text-xs font-semibold text-muted-foreground dark:border-[var(--tp-border-strong)] dark:bg-[color-mix(in_srgb,var(--tp-muted)_88%,var(--tp-bg-surface))] dark:text-[var(--tp-color-text-500)]'
);

/** 操作列等右对齐（原 `.tp-text-end`） */
export const tableCellAlignEndClass = 'text-right';

export const tableBodyCell = cva(
  'border-b border-[color-mix(in_srgb,var(--tp-border-default)_65%,transparent)] px-[14px] py-3 align-middle text-[0.8125rem] whitespace-normal break-words [overflow-wrap:anywhere]'
);

export const tableBodyRow = cva(
  'transition-[background-color,box-shadow] duration-150 hover:bg-[color-mix(in_srgb,var(--tp-color-primary-600)_4%,var(--tp-bg-surface))] dark:hover:bg-[color-mix(in_srgb,var(--tp-accent)_55%,transparent)]'
);

export const tableRowSelected = cva(
  'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_7%,var(--tp-bg-surface))] shadow-[inset_3px_0_0_var(--tp-color-primary-600)]'
);

export const tableToolbarRoot = cva(
  'flex flex-wrap items-end justify-between gap-3'
);

export const tableToolbarMeta = cva('min-w-0 shrink-0');

export const tableToolbarTitle = cva('text-[0.9375rem] font-bold text-foreground');

export const tableToolbarSubtitle = cva('mt-1 text-[0.8125rem] text-muted-foreground');

/** #meta 插槽默认样式（分页摘要等，置于标题/副标题之下） */
export const tableToolbarMetaLine = cva('mt-1 text-sm leading-snug text-[var(--tp-color-text-500)]');

export const tableToolbarFilters = cva(
  'flex min-w-0 flex-1 flex-wrap items-center justify-end gap-2'
);

export const tableToolbarActions = cva('flex flex-wrap items-center justify-end gap-2');

export const tableFilterFormClass = 'flex flex-wrap items-center justify-end gap-2';

/** 与下拉同排时勿 flex-grow；宽度接近 TableFilterSelect（约「全部优先级」量级） */
export const tableFilterInputWidth = cva('w-[8.75rem] max-w-full shrink-0 flex-none');

export const tableFilterSelectWidth = cva('w-auto min-w-[8.75rem] shrink-0');
