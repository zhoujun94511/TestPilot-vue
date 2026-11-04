import { cn } from '@/lib/utils';

/** Cases 页领域样式（原 CasesView scoped） */

export const casesSyncHighlightClass = cn(
  'outline outline-2 outline-[color-mix(in_srgb,var(--tp-color-primary-500)_55%,transparent)]',
  'transition-[outline-color] duration-200 ease-out'
);

export const casesExportFormatClass =
  'h-10 w-[120px] shrink-0 grow-0 basis-[120px]';

export const casesFormLabelPlaceholderClass =
  'invisible mb-1.5';

export const casesCellClamp2Class =
  'line-clamp-2 overflow-hidden [overflow-wrap:anywhere] leading-[1.45]';

export const casesCellClamp3Class =
  'line-clamp-3 overflow-hidden leading-[1.45]';

export const casesCellMetaClass = cn(casesCellClamp3Class, 'mt-0.5');

export const casesActionsClass =
  'flex flex-nowrap justify-end gap-2 [&_button]:whitespace-nowrap [&_a]:whitespace-nowrap';

export const casesRowHighlightClass = cn(
  'bg-[color-mix(in_srgb,var(--tp-color-primary-500)_34%,transparent)]',
  'animate-cases-row-highlight-fade'
);
