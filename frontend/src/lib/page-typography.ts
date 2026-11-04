import { cn } from '@/lib/utils';
import { surfaceNestedBlockClass } from '@/lib/surface-ui';

/** 页面标题 / KPI / 列表（Dashboard 等）Tailwind 类，替代 components.css 中部分 .tp-* */

export const sectionTitleClass =
  'text-base font-bold text-[var(--tp-color-text-900)]';

export const sectionTitleHeroClass =
  'text-base font-bold text-[var(--tp-color-ai-600)]';

/** Dashboard 欢迎区主标题（原 `.tp-page-title__heading`） */
export const welcomePageHeadingClass =
  'm-0 text-[1.9rem] font-bold leading-[1.2] text-[var(--tp-color-text-900)]';

/** Dashboard 欢迎区副标题（原 `.tp-page-title__subtitle`） */
export const welcomePageSubtitleClass =
  'mb-0 mt-2 max-w-[72ch] text-[var(--tp-color-text-500)]';

export const sectionSubtitleClass =
  'mt-1 text-sm leading-snug text-[var(--tp-color-text-500)]';

/** TpCard 副标题（原 `.tp-card__subtitle`） */
export const cardSubtitleClass =
  'text-sm leading-snug text-[var(--tp-color-text-500)]';

export const dataTitleClass =
  'font-semibold text-[var(--tp-color-text-900)]';

export const dataSubtitleClass =
  'mt-1 text-sm leading-normal text-[var(--tp-color-text-500)]';

/** 表格/列表单元格副标题（无额外上边距） */
export const dataSubtitleDenseClass =
  'text-sm leading-normal text-[var(--tp-color-text-500)]';

export const resultListClass = 'grid gap-2.5';

export const resultItemClass = cn(
  surfaceNestedBlockClass,
  'p-3.5 transition-[background-color,border-color,transform] duration-150 hover:-translate-y-px hover:border-[color-mix(in_srgb,var(--tp-color-primary-600)_20%,var(--tp-border-default))] hover:bg-[color-mix(in_srgb,var(--tp-color-primary-600)_4%,var(--tp-bg-subtle))]'
);

export const brandNameClass = 'text-base font-bold text-[var(--tp-color-text-900)]';

/** 侧栏品牌副标题：窄宽下单行省略，不用 uppercase（中英文都更省宽度） */
export const brandSubtitleClass =
  'mt-0.5 truncate text-[0.6875rem] font-medium leading-tight tracking-normal text-[var(--tp-color-text-500)]';

/**
 * 顶栏 kicker（`common.shell.pageKicker`）
 * 桌面侧栏已展示品牌，≥1200px 隐藏以免与侧栏 IA 重复；窄屏抽屉模式保留作上下文锚点。
 */
export const shellPageKickerClass =
  'mb-0.5 text-[0.68rem] font-bold uppercase leading-none tracking-[0.1em] text-[var(--tp-color-text-500)] max-[1199px]:block min-[1200px]:hidden';

export const pageContextClass =
  'mt-1.5 text-lg font-bold leading-tight tracking-tight text-[var(--tp-color-text-900)]';

export const pageSubtitleClass =
  'mt-1.5 max-w-[72ch] text-sm leading-snug text-muted-foreground';

export const kpiLabelClass =
  'text-[0.78rem] font-bold uppercase tracking-[0.08em] text-[var(--tp-color-text-500)]';

export const kpiValueClass =
  'mt-1.5 text-[1.9rem] font-extrabold leading-none text-[var(--tp-color-text-900)]';

export const kpiHintClass =
  'mt-2.5 text-sm text-[var(--tp-color-text-500)]';

export const kpiIconClass =
  'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[color-mix(in_srgb,var(--tp-color-primary-600)_12%,var(--tp-bg-subtle))] text-base text-[var(--tp-color-primary-600)]';

/** KPI 内容区（外缘由 TpCard / PagePanel 承担，避免双边框叠影） */
export const kpiCardShellClass =
  'flex min-h-[98px] min-w-0 flex-col justify-between';

export const activityListClass = 'grid gap-2.5';

export const activityItemClass = cn(
  surfaceNestedBlockClass,
  'p-3.5 transition-[background-color,border-color,transform] duration-150 hover:-translate-y-px hover:border-[color-mix(in_srgb,var(--tp-color-primary-600)_20%,var(--tp-border-default))] hover:bg-[color-mix(in_srgb,var(--tp-color-primary-600)_4%,var(--tp-bg-subtle))]'
);

/** 嵌套面板内的 KPI 数字块（替代内层 TpCard） */
export const nestedMetricBlockClass = cn(surfaceNestedBlockClass, 'flex min-h-[98px] flex-col justify-between');

export const dashboardHeroCardClass =
  'bg-[color-mix(in_srgb,var(--tp-bg-surface)_96%,var(--tp-color-primary-600)_4%)]';

export const inlineToggleLabelClass =
  'inline-flex items-center gap-2.5 text-sm font-semibold text-[var(--tp-color-text-600)]';

/** 辅助说明 / 审计行（原 `.tp-small`） */
export const captionTextClass = 'text-sm leading-snug';
