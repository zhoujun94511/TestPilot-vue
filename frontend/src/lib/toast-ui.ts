import { cva, type VariantProps } from 'class-variance-authority';
import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { cn } from '@/lib/utils';

export type AppToastType = 'success' | 'warning' | 'danger' | 'info';

/** Vue TransitionGroup `name`（样式见 styles/feedback.css） */
export const APP_TOAST_TRANSITION_NAME = 'app-toast';

export const appToastStackClass = cn(
  'pointer-events-none fixed bottom-4 right-4 z-[1400] grid w-[min(420px,calc(100vw-32px))] gap-2.5',
  'max-md:left-4 max-md:right-4 max-md:w-auto'
);

export const appToastItemClass = cva(
  cn(
    'pointer-events-auto grid grid-cols-[auto_1fr_auto] items-start gap-3',
    'rounded-[var(--tp-radius-lg)] border border-[var(--tp-border-default)]',
    'bg-[var(--tp-bg-surface)] px-3.5 py-3 shadow-[var(--tp-shadow-lg)]',
    'dark:border-[var(--tp-border-strong)] dark:bg-[color-mix(in_srgb,var(--tp-bg-surface)_94%,var(--tp-bg-page))]'
  ),
  {
    variants: {
      type: {
        success:
          'border-[color-mix(in_srgb,var(--tp-color-success-600)_35%,var(--tp-border-default))]',
        warning:
          'border-[color-mix(in_srgb,var(--tp-color-warning-600)_35%,var(--tp-border-default))]',
        danger:
          'border-[color-mix(in_srgb,var(--tp-color-danger-600)_35%,var(--tp-border-default))]',
        info: 'border-[color-mix(in_srgb,var(--tp-color-info-600)_35%,var(--tp-border-default))]'
      }
    },
    defaultVariants: {
      type: 'info'
    }
  }
);

export type AppToastItemTone = NonNullable<VariantProps<typeof appToastItemClass>['type']>;

export const appToastIconClass = cva('mt-0.5 inline-flex', {
  variants: {
    type: {
      success: 'text-[var(--tp-color-success-600)]',
      warning: 'text-[var(--tp-color-warning-600)]',
      danger: 'text-[var(--tp-color-danger-600)]',
      info: 'text-[var(--tp-color-info-600)]'
    }
  },
  defaultVariants: {
    type: 'info'
  }
});

export const appToastBodyClass = 'grid min-w-0 gap-0.5';

export const appToastTitleClass =
  'text-[0.8125rem] font-bold text-[var(--tp-color-text-900)]';

export const appToastMessageClass =
  'text-[0.8125rem] leading-[1.45] text-[var(--tp-color-text-600)]';

export const appToastCloseClass = cn(
  'inline-flex cursor-pointer items-center justify-center rounded-[var(--tp-radius-sm)] border-0 bg-transparent p-1',
  'text-[var(--tp-color-text-500)] hover:bg-muted hover:text-[var(--tp-color-text-900)]',
  interactiveFocusRingClass
);
