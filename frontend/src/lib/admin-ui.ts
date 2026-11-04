import { cn } from '@/lib/utils';
import { grid12Class } from '@/lib/page-layout-ui';

/** 用户管理等页内嵌创建表单外框 */
export const adminInlineFormShellClass = cn(
  'mb-6 flex flex-col gap-4 rounded-lg border border-[var(--tp-border-default)]',
  'bg-[color-mix(in_srgb,var(--tp-bg-subtle)_35%,var(--tp-bg-surface))] p-4 md:p-5'
);

/** 表单内分行容器（避免 5 个字段挤在一个 auto-flow 网格里错位） */
export const adminInlineFormBodyClass = 'flex flex-col gap-4';

/** 同一行多列；标签区高度须一致（说明放表单头或控件下方，勿插在 label 与 input 之间） */
export const adminInlineFormRowClass = cn(grid12Class, 'items-start gap-x-4 gap-y-4');

export const adminInlineFormHeaderClass = 'min-w-0 space-y-1';
