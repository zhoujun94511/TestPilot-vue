import { cva, type VariantProps } from 'class-variance-authority';
import { surfacePanelClass } from '@/lib/surface-ui';
import { cn } from '@/lib/utils';

export type DashboardActivityTone = NonNullable<
  VariantProps<typeof dashboardActivityIconClass>['tone']
>;

export const dashboardActivityIconClass = cva(
  'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] text-[0.72rem] font-bold',
  {
    variants: {
      tone: {
        primary:
          'text-[var(--tp-color-primary-600)] bg-[color-mix(in_srgb,var(--tp-color-primary-600)_10%,var(--tp-bg-subtle))]',
        success:
          'text-[var(--tp-color-success-600)] bg-[color-mix(in_srgb,var(--tp-color-success-600)_10%,var(--tp-bg-subtle))]',
        info: 'text-[var(--tp-color-info-600)] bg-[color-mix(in_srgb,var(--tp-color-info-600)_10%,var(--tp-bg-subtle))]',
        warning:
          'text-[var(--tp-color-warning-600)] bg-[color-mix(in_srgb,var(--tp-color-warning-600)_10%,var(--tp-bg-subtle))]',
        muted: 'text-[var(--tp-color-text-500)]'
      }
    },
    defaultVariants: {
      tone: 'primary'
    }
  }
);

const legacyActivityColorMap: Record<string, DashboardActivityTone> = {
  'tp-text-primary': 'primary',
  'tp-text-success': 'success',
  'tp-text-info': 'info',
  'tp-text-warning': 'warning',
  'tp-activity-icon--muted': 'muted',
  primary: 'primary',
  success: 'success',
  info: 'info',
  warning: 'warning',
  muted: 'muted'
};

/** 活动行图标色（兼容 API / fallback 的旧 utility 类名） */
export function resolveDashboardActivityTone(color?: string | null): DashboardActivityTone {
  if (!color) return 'primary';
  return legacyActivityColorMap[color] ?? 'primary';
}

export const aiCapabilityCardClass =
  'flex min-h-[156px] flex-col justify-between';

export const aiCapabilityProgressPlaceholderClass = 'h-7';

export const systemLayoutClass = 'grid gap-4';

/** 总览区块：单层边框容器，避免「大卡片套小卡片」 */
export const dashboardBlockClass = cn(surfacePanelClass, 'p-[var(--tp-space-4)]');

export const dashboardBlockHeaderClass = 'mb-[var(--tp-space-3)]';

/** 系统状态内层：始终纵向堆叠（整体状态在上、四宫格在下），适配 5/12 窄列 */
export const systemSummaryClass = cn(
  'grid grid-cols-1 gap-4 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-4'
);

export const systemSummaryMainClass = 'grid content-start gap-2.5';

export const systemSummaryStatusClass =
  'text-[1.85rem] font-extrabold leading-[1.05] text-[var(--tp-color-text-900)]';

export const systemSummaryDescriptionClass =
  'max-w-[32ch] leading-relaxed text-[var(--tp-color-text-500)]';

export const systemSummaryGridClass = 'grid grid-cols-1 gap-3 sm:grid-cols-2';

export const systemSummaryCardClass = cn(
  'min-w-0 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] p-3.5'
);

export const systemSummaryCardHeaderClass =
  'flex items-start justify-between gap-3';

export const systemSummaryCardHintClass =
  'mt-2.5 text-sm leading-[1.55] text-[var(--tp-color-text-500)] [overflow-wrap:anywhere]';

/** 顶区：模型 / 覆盖 / 可靠性（单面板三列，避免 hero 套小卡） */
export const dashboardPulsePanelClass = cn(
  surfacePanelClass,
  'p-[var(--tp-space-4)] shadow-[var(--tp-shadow-sm)]',
  'bg-[color-mix(in_srgb,var(--tp-bg-surface)_96%,var(--tp-color-primary-600)_4%)]'
);

export const dashboardPulseGridClass = 'grid grid-cols-1 gap-4 sm:grid-cols-2';

export const dashboardPulseItemClass = cn(
  'min-w-0 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-4',
  'flex min-h-[8.75rem] flex-col justify-between'
);

export const dashboardHealthListClass = 'grid gap-2';

/** 全宽系统状态卡：宽屏三列明细，与快捷入口同宽 */
export const dashboardHealthListWideClass =
  'grid grid-cols-1 gap-2 md:grid-cols-2 min-[1200px]:grid-cols-3';

export const dashboardHealthRowClass = cn(
  'flex min-w-0 items-start gap-3 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] px-3.5 py-3'
);

export const dashboardHealthRowMainClass = 'min-w-0 flex-1';

export const dashboardHealthRowTitleClass = 'font-semibold text-[var(--tp-color-text-900)]';

export const dashboardHealthRowHintClass =
  'mt-1 text-sm leading-snug text-[var(--tp-color-text-500)] [overflow-wrap:anywhere]';

export const dashboardHealthDotClass = cva('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', {
  variants: {
    tone: {
      success: 'bg-[var(--tp-color-success-600)]',
      warning: 'bg-[var(--tp-color-warning-600)]',
      danger: 'bg-[var(--tp-color-danger-600)]',
      neutral: 'bg-[var(--tp-color-text-400)]'
    }
  },
  defaultVariants: { tone: 'neutral' }
});

export const dashboardShortcutGridClass = 'grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4';

export const dashboardShortcutTileClass = cn(
  'flex items-start gap-3 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-3.5 no-underline',
  'transition-[background-color,border-color,transform] duration-150',
  'hover:-translate-y-px hover:border-[color-mix(in_srgb,var(--tp-color-primary-600)_22%,var(--tp-border-default))]',
  'hover:bg-[color-mix(in_srgb,var(--tp-color-primary-600)_5%,var(--tp-bg-subtle))]',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring'
);

export const dashboardShortcutTileIconClass =
  'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[color-mix(in_srgb,var(--tp-color-primary-600)_12%,var(--tp-bg-surface))] text-[var(--tp-color-primary-600)]';

export const dashboardShortcutTileTitleClass = 'block text-sm font-semibold text-[var(--tp-color-text-900)]';

export const dashboardShortcutTileDescClass = 'mt-0.5 block text-xs leading-snug text-[var(--tp-color-text-500)]';

/** 与快捷入口同密度：浅底内嵌块，无额外 min-height / 双层阴影 */
export const dashboardStatTileClass = dashboardShortcutTileClass;

export const dashboardStatTileLabelClass =
  'block text-[0.72rem] font-bold uppercase tracking-[0.06em] text-[var(--tp-color-text-500)]';

export const dashboardStatTileValueClass =
  'block mt-0.5 text-xl font-extrabold leading-tight text-[var(--tp-color-text-900)]';

export const dashboardStatTileHeadRowClass = 'flex flex-wrap items-center justify-between gap-2';

/** 数值在右侧时：与高级指标等紧凑行标题一致（非全大写） */
export const dashboardStatTileTitleInlineClass =
  'min-w-0 font-semibold text-[var(--tp-color-text-900)]';

export const dashboardStatTileValueEndClass =
  'shrink-0 text-xl font-extrabold leading-tight tabular-nums text-[var(--tp-color-text-900)]';

export const dashboardStatTileHintClass = dashboardShortcutTileDescClass;

/** 高级指标全宽：宽屏四列 */
export const dashboardAdvancedListWideClass =
  'grid grid-cols-1 gap-2 md:grid-cols-2 min-[1200px]:grid-cols-4';

/** 高级指标侧栏（与最近活动左右分栏） */
export const dashboardAdvancedListSideClass = 'grid grid-cols-1 gap-2';

/** 最近活动条数超过该值时，列表区域出现纵向滚动条 */
export const ACTIVITY_SCROLL_THRESHOLD = 6;

export function dashboardActivityPanelClass(enableScroll: boolean) {
  return cn(
    'grid gap-2',
    enableScroll &&
      'tp-subtle-scrollbar max-h-[min(28rem,52vh)] min-h-0 overflow-y-auto overscroll-y-contain [scrollbar-width:thin] pr-0.5'
  );
}

export const dashboardActivityGroupClass =
  'overflow-hidden rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)]';

export const dashboardActivityGroupHeaderClass = cn(
  'flex w-full cursor-pointer items-start gap-3 border-0 bg-transparent px-3.5 py-3 text-left',
  'transition-colors hover:bg-[color-mix(in_srgb,var(--tp-color-primary-600)_4%,var(--tp-bg-subtle))]',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring'
);

export const dashboardActivityGroupItemClass =
  'border-t border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] px-3.5 py-2.5 first:border-t-0';

/** 总览顶栏左侧：模型 / 可靠性 / 整体健康 / 更新时间 */
export const dashboardMetaStripClass =
  'flex min-w-0 flex-wrap items-center justify-start gap-x-2 gap-y-1.5';
