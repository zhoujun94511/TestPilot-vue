import { cn } from '@/lib/utils';

/** 文档模块表格/历史页样式 */

export const historyCellSourceClass = 'max-w-[200px] truncate';

export const documentsRawBlockClass = cn(
  'm-0 whitespace-pre-wrap break-words rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)]',
  'bg-[var(--tp-bg-subtle)] p-3.5 font-[family-name:var(--tp-font-mono)] text-[0.78rem] leading-normal',
  'text-[var(--tp-color-text-500)]'
);

export const documentsAnalysisRequirementItemClass = cn(
  'rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] !p-2.5',
  'bg-[color-mix(in_srgb,var(--tp-bg-surface)_94%,var(--tp-color-primary-600)_6%)]'
);

export const documentsRequirementHighlightClass = 'doc-requirement-highlight';

export const documentsRowHighlightClass = 'doc-row-highlight';

export const documentsRequirementHighlightActiveClass = cn(
  documentsRequirementHighlightClass,
  'outline outline-2 outline-[color-mix(in_srgb,var(--tp-color-primary-600)_45%,transparent)]',
  'transition-[outline-color] duration-200 ease-out'
);

export const documentsRowHighlightActiveClass = cn(
  documentsRowHighlightClass,
  'bg-[color-mix(in_srgb,var(--tp-color-primary-500)_14%,transparent)] animate-doc-row-highlight-fade'
);
