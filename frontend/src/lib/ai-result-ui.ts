import { cn } from '@/lib/utils';

export const aiResultCardClass = cn(
  'border border-[color-mix(in_srgb,var(--tp-color-ai-600)_32%,var(--tp-border-default))]',
  'bg-[var(--tp-bg-subtle)]'
);

export const aiResultHeadClass =
  'mb-3.5 flex items-start justify-between gap-4';

export const aiResultTitleClass =
  'text-base font-bold text-[var(--tp-color-text-900)]';

export const aiResultSubtitleClass =
  'mt-1 text-sm text-[var(--tp-color-text-500)]';

export const aiResultMetaClass = 'flex flex-wrap justify-end gap-2';

export const aiResultSectionClass = 'mt-3.5 first:mt-0';

export const aiResultSectionTitleClass =
  'mb-2 text-[0.78rem] font-bold uppercase tracking-[0.08em] text-[var(--tp-color-text-500)]';

export const aiResultCollapseSectionClass = cn(
  aiResultSectionClass,
  'mt-3 border-t border-[var(--tp-border-default)] pt-3'
);

export const aiResultCollapseToggleClass =
  'inline-flex cursor-pointer items-center gap-1.5 border-0 bg-transparent p-0 font-bold text-[var(--tp-color-primary-600)]';

export const aiResultCollapseContentClass = 'mt-2.5';
