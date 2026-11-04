import { cn } from '@/lib/utils';

/** 页面级面板 / TpCard 外框（单一来源，避免 Card 基元再叠一层 border/shadow） */
export const surfacePanelClass = cn(
  'min-w-0 rounded-[var(--tp-radius-lg)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] shadow-[var(--tp-shadow-sm)]',
  'dark:border-[var(--tp-border-strong)] dark:bg-[color-mix(in_srgb,var(--tp-bg-surface)_92%,var(--tp-bg-subtle))]'
);

/** 面板内的指标块 / 列表项（不再套 TpCard） */
export const surfaceNestedBlockClass = cn(
  'min-w-0 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-4',
  'dark:border-[var(--tp-border-strong)] dark:bg-[var(--tp-bg-elevated)]'
);
