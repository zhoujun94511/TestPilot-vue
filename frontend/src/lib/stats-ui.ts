import { cn } from '@/lib/utils';

/** 列表页 KPI 分格外框（知识库 / 用例管理等共用） */
export const statsSummaryPanelClass = cn(
  'rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-3.5'
);

/** 分格内的单指标卡（surface 底 + 轻阴影，与外层 subtle 区分） */
export const statsSummaryMetricClass = cn(
  'min-w-0 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] p-3.5',
  'flex min-h-[5.5rem] flex-col justify-between shadow-[var(--tp-shadow-sm)]'
);
