import { cva } from 'class-variance-authority';
import type { ClassValue } from 'clsx';
import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { cn } from '@/lib/utils';

/** 表单标签 / 帮助文案（原 `.tp-form-label`、`.tp-help-text`） */

/** 内描边 focus，避免外圈 ring 被壳层 overflow 裁切 */
export const fieldFocusRingClass = cn(
  interactiveFocusRingClass,
  'focus-visible:border-[var(--tp-border-strong)]'
);

/** 输入/选择/文本域共用壳（不含尺寸） */
export const fieldControlShellClass = cn(
  'box-border max-w-full flex w-full rounded-md border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] text-sm text-foreground transition-[color,box-shadow,border-color]',
  'placeholder:text-[var(--tp-color-text-placeholder)]',
  'hover:border-[var(--tp-border-strong)]',
  'disabled:cursor-not-allowed disabled:border-[var(--tp-border-default)] disabled:bg-[color-mix(in_srgb,var(--tp-bg-subtle)_55%,var(--tp-bg-surface))] disabled:text-[var(--tp-color-text-600)] disabled:opacity-100',
  fieldFocusRingClass
);

export const formLabelClass =
  'mb-2 inline-flex items-center gap-2 text-sm font-semibold text-[var(--tp-color-text-600)]';

export const helpTextClass =
  'text-[0.78rem] leading-snug text-[var(--tp-color-text-500)]';

/** 说明在控件下方（默认） */
export const helpTextBelowFieldClass = cn(helpTextClass, 'mt-1.5');

/** 说明在标签与控件之间（大文本域等，避免 helper 被顶到块底部） */
export const helpTextBelowLabelClass = cn(helpTextClass, 'mb-2.5');

export const fieldRootClass = 'grid min-w-0 gap-0';

export const fieldRequiredMarkClass =
  'ml-1 text-[var(--tp-color-danger-600)]';

export const fieldDirtyTagClass = 'min-w-14 justify-center';

export const fieldMetaClass = 'mt-1.5';

export const fieldErrorTextClass =
  'text-[0.78rem] leading-snug text-[var(--tp-color-danger-600)]';

const fieldControlBase = cn(fieldControlShellClass, 'px-3 py-2');

/** 固定 h-* 与 py-2 同用会裁切原生控件文字（Windows select 尤甚） */
const FIXED_HEIGHT_CLASS = /\bh-(?:7|8|9|10|11|12)\b/;
const LEADING_FOR_HEIGHT: Record<string, string> = {
  '7': 'leading-7',
  '8': 'leading-8',
  '9': 'leading-9',
  '10': 'leading-10',
  '11': 'leading-11',
  '12': 'leading-12'
};

export function mergeControlSizeClass(...parts: ClassValue[]) {
  const merged = cn(...parts);
  if (!merged || !FIXED_HEIGHT_CLASS.test(merged)) {
    return merged;
  }
  const height = merged.match(/\bh-(7|8|9|10|11|12)\b/)?.[1];
  return cn(merged, 'py-0', height ? LEADING_FOR_HEIGHT[height] : undefined);
}

export const inputVariants = cva(
  cn(fieldControlShellClass, 'h-10 px-3 py-0 leading-10')
);
const selectChevronLight =
  'url("data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%20width=%2716%27%20height=%2716%27%20viewBox=%270%200%2024%2024%27%20fill=%27none%27%20stroke=%27%23475569%27%20stroke-width=%272%27%20stroke-linecap=%27round%27%20stroke-linejoin=%27round%27%3E%3Cpath%20d=%27m6%209%206%206%206-6%27/%3E%3C/svg%3E")';
const selectChevronDark =
  'url("data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%20width=%2716%27%20height=%2716%27%20viewBox=%270%200%2024%2024%27%20fill=%27none%27%20stroke=%27%23a8b4c4%27%20stroke-width=%272%27%20stroke-linecap=%27round%27%20stroke-linejoin=%27round%27%3E%3Cpath%20d=%27m6%209%206%206%206-6%27/%3E%3C/svg%3E")';
const selectChevronClass = cn(
  'cursor-pointer bg-[length:1rem_1rem] bg-[position:right_0.65rem_center] bg-no-repeat pr-9',
  `[background-image:${selectChevronLight}]`,
  `dark:[background-image:${selectChevronDark}]`
);

/** 原生 select 固定高度时勿叠 py-2，否则中文选项会被裁切（Windows 尤甚） */
export const selectVariants = cva(
  cn(
    fieldControlShellClass,
    selectChevronClass,
    'h-10 px-3 py-0 leading-10 [color-scheme:light] dark:[color-scheme:dark]'
  )
);

export const selectCompactVariants = cva(
  cn(
    fieldControlShellClass,
    selectChevronClass,
    'h-9 px-3 py-0 text-sm leading-9 [color-scheme:light] dark:[color-scheme:dark]'
  )
);
export const textareaVariants = cva(`${fieldControlBase} min-h-[120px] resize-y py-2`);

/** Provider 快捷面板等紧凑原生 input */
export const compactInputVariants = cva(
  cn(
    fieldControlShellClass,
    'h-9 px-2.5 py-0 text-xs leading-9 bg-[var(--tp-bg-page)] text-[var(--tp-color-text-900)]'
  )
);
