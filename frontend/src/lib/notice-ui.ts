import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import { PAGE_NOTICE_BANNER_MARKER } from '@/lib/page-chrome-ui';

export type RiskBlockTone = 'warning' | 'danger' | 'info' | 'success';

export const riskBlockPanelClass = cva(
  'rounded-[var(--tp-radius-md)] border-l-4 px-3.5 py-3 text-[var(--tp-color-text-900)]',
  {
    variants: {
      tone: {
        warning:
          'border-l-[var(--tp-color-warning-600)] bg-[color-mix(in_srgb,var(--tp-color-warning-600)_8%,var(--tp-bg-surface))]',
        danger:
          'border-l-[var(--tp-color-danger-600)] bg-[color-mix(in_srgb,var(--tp-color-danger-600)_8%,var(--tp-bg-surface))]',
        info: 'border-l-[var(--tp-color-info-600)] bg-[color-mix(in_srgb,var(--tp-color-info-600)_8%,var(--tp-bg-surface))]',
        success:
          'border-l-[var(--tp-color-success-600)] bg-[color-mix(in_srgb,var(--tp-color-success-600)_8%,var(--tp-bg-surface))]'
      }
    },
    defaultVariants: {
      tone: 'warning'
    }
  }
);

export type RiskBlockPanelTone = NonNullable<VariantProps<typeof riskBlockPanelClass>['tone']>;

export const riskBlockTitleClass = 'mb-1 font-bold';

export const riskBlockTextClass = 'text-sm text-[var(--tp-color-text-600)]';

/** 与旧 CSS 一致：success/info 页级 toast 不展示 */
export function isPageNoticeToastSuppressed(type: RiskBlockTone): boolean {
  return type === 'success' || type === 'info';
}

/** PageNoticeBanner 内 ghost 按钮标记（TpButton CVA，非 `.tp-btn--ghost`） */
export const pageNoticeGhostButtonClass = 'page-notice-ghost-btn';

const pageNoticeToneShell = {
  danger: cn(
    'border-[color-mix(in_srgb,var(--tp-notice-danger-accent)_44%,var(--tp-border-default))]',
    'bg-[var(--tp-notice-danger-bg)] text-[var(--tp-notice-danger-fg)]',
    '[&_.page-notice-ghost-btn]:text-[var(--tp-notice-danger-fg)]'
  ),
  warning: cn(
    'border-[color-mix(in_srgb,var(--tp-notice-warning-accent)_44%,var(--tp-border-default))]',
    'bg-[var(--tp-notice-warning-bg)] text-[var(--tp-notice-warning-fg)]',
    '[&_.page-notice-ghost-btn]:text-[var(--tp-notice-warning-fg)]'
  ),
  success: cn(
    'border-[color-mix(in_srgb,var(--tp-notice-success-accent)_44%,var(--tp-border-default))]',
    'bg-[var(--tp-notice-success-bg)] text-[var(--tp-notice-success-fg)]',
    '[&_.page-notice-ghost-btn]:text-[var(--tp-notice-success-fg)]'
  ),
  info: cn(
    'border-[color-mix(in_srgb,var(--tp-notice-info-accent)_44%,var(--tp-border-default))]',
    'bg-[var(--tp-notice-info-bg)] text-[var(--tp-notice-info-fg)]',
    '[&_.page-notice-ghost-btn]:text-[var(--tp-notice-info-fg)]'
  )
} as const;

const pageNoticeGhostBtnClass = cn(
  '[&_.page-notice-ghost-btn]:border',
  '[&_.page-notice-ghost-btn]:bg-[color-mix(in_srgb,var(--tp-bg-surface)_82%,var(--tp-bg-subtle))]',
  'dark:[&_.page-notice-ghost-btn]:bg-[color-mix(in_srgb,var(--tp-bg-surface)_55%,var(--tp-bg-page))]',
  '[&_.page-notice-ghost-btn:hover]:bg-[color-mix(in_srgb,var(--page-notice-accent)_12%,var(--tp-bg-surface))]',
  'dark:[&_.page-notice-ghost-btn:hover]:bg-[color-mix(in_srgb,var(--page-notice-accent)_18%,var(--tp-bg-surface))]',
  '[&_.page-notice-ghost-btn]:border-[color-mix(in_srgb,var(--page-notice-accent)_30%,var(--tp-border-default))]'
);

export const pageNoticeBannerShellClass = cva(
  cn(
    PAGE_NOTICE_BANNER_MARKER,
    'relative fixed bottom-[22px] left-1/2 z-[1250] m-0 w-[min(720px,calc(100vw-28px))] -translate-x-1/2',
    'rounded-xl border p-3.5 pl-12 shadow-[var(--tp-shadow-notice)] backdrop-blur-[4px]',
    'animate-page-toast-in',
    'max-md:bottom-3 max-md:w-[calc(100vw-16px)] max-md:rounded-[10px] max-md:p-2.5 max-md:pl-[42px]',
    pageNoticeGhostBtnClass
  ),
  {
    variants: {
      tone: pageNoticeToneShell
    },
    defaultVariants: {
      tone: 'info'
    }
  }
);

export const pageNoticeBannerIconWrapClass = cn(
  'pointer-events-none absolute left-3.5 top-1/2 flex h-[22px] w-[22px] -translate-y-1/2',
  'items-center justify-center rounded-full text-[13px] font-extrabold leading-none text-[var(--tp-color-text-inverse)]',
  'max-md:left-3 max-md:h-5 max-md:w-5 max-md:text-xs'
);

export const pageNoticeBannerIconSurfaceClass = cva('', {
  variants: {
    tone: {
      danger: 'bg-[var(--tp-notice-danger-accent)]',
      warning: 'bg-[var(--tp-notice-warning-accent)]',
      success: 'bg-[var(--tp-notice-success-accent)]',
      info: 'bg-[var(--tp-notice-info-accent)]'
    }
  },
  defaultVariants: {
    tone: 'info'
  }
});

export const pageNoticeBannerMessageClass = cva('whitespace-pre-wrap break-words text-sm', {
  variants: {
    tone: {
      danger: 'text-[var(--tp-notice-danger-fg-emphasis)]',
      warning: 'text-[var(--tp-notice-warning-fg-emphasis)]',
      success: 'text-[var(--tp-notice-success-fg-emphasis)]',
      info: 'text-[var(--tp-notice-info-fg-emphasis)]'
    }
  },
  defaultVariants: {
    tone: 'info'
  }
});

const NOTICE_ACCENT_VAR: Record<RiskBlockTone, string> = {
  danger: 'var(--tp-notice-danger-accent)',
  warning: 'var(--tp-notice-warning-accent)',
  success: 'var(--tp-notice-success-accent)',
  info: 'var(--tp-notice-info-accent)'
};

export function pageNoticeAccentVar(tone: RiskBlockTone): string {
  return NOTICE_ACCENT_VAR[tone];
}

export function pageNoticeIconGlyph(tone: RiskBlockTone): string {
  if (tone === 'success') return '✓';
  if (tone === 'warning') return '!';
  if (tone === 'danger') return '×';
  return 'i';
}
