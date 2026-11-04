import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { cn } from '@/lib/utils';

/** 上传页字段 / 进度条（Documents / Knowledge Upload） */

export const uploadPanelClass = 'grid gap-2.5';

export const uploadPanelRowClass =
  'flex flex-wrap items-stretch gap-2.5 md:flex-nowrap';

export const uploadPanelSelectionClass = cn(
  'flex min-w-0 flex-1 cursor-pointer items-center overflow-hidden text-ellipsis whitespace-nowrap max-md:w-full md:min-w-[220px]',
  'rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] px-3',
  'text-[var(--tp-color-text-500)]',
  interactiveFocusRingClass,
  'rounded-[var(--tp-radius-md)]'
);

export const uploadPanelNativeInputClass = 'hidden';

export const uploadPanelPickerClass = cn(
  'shrink-0 cursor-pointer rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)]',
  'bg-[var(--tp-bg-subtle)] px-3 py-[11px] text-sm font-semibold text-[var(--tp-color-text-600)]',
  'disabled:cursor-not-allowed disabled:opacity-60'
);

export const uploadPanelFooterClass =
  'flex flex-wrap items-center justify-between gap-2.5';

export const uploadPanelFilenameClass =
  'text-sm text-[var(--tp-color-text-500)]';

export const uploadCategoryFieldClass =
  'mb-4 w-full min-w-[220px] max-w-[360px]';

export const uploadProgressLabelClass =
  'mb-1.5 text-xs text-[var(--tp-color-text-500)]';

export const uploadProgressTrackClass =
  'h-1.5 w-full overflow-hidden rounded-full bg-[var(--tp-bg-subtle)]';

export const uploadProgressFillClass =
  'h-full bg-[var(--tp-color-primary-600)] transition-[width] duration-200';

export const docUploadAutoToggleClass = 'mt-2 inline-flex max-w-full';
