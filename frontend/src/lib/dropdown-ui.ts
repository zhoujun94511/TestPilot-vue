import { cn } from '@/lib/utils';

/** 与 surfacePanel / 顶栏操作条同源的浮层菜单外框（ToolbarOverflowMenu 等） */
export const dropdownMenuContentClass = cn(
  'z-50 min-w-[11rem] overflow-hidden p-1',
  'rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)]',
  'bg-[var(--tp-bg-surface)] text-[var(--tp-foreground)] shadow-[var(--tp-shadow-md)] ring-1 ring-[color-mix(in_srgb,var(--tp-border-default)_55%,transparent)]',
  'dark:border-[var(--tp-border-strong)] dark:bg-[var(--tp-bg-elevated)] dark:shadow-[var(--tp-shadow-lg)]'
);

export const dropdownMenuLabelClass =
  'px-2 py-1.5 text-xs font-semibold text-[var(--tp-color-text-500)]';

export const dropdownMenuItemClass = cn(
  'rounded-[calc(var(--tp-radius-md)-4px)] text-sm font-medium',
  /* Reka/Radix 用 data-highlighted 表示悬停与键盘高亮，仅用 focus: 无法覆盖鼠标悬停 */
  'data-[highlighted]:bg-[var(--tp-accent)] data-[highlighted]:text-[var(--tp-accent-foreground)]',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--tp-ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--tp-bg-surface)]'
);

export const dropdownMenuSeparatorClass = 'my-1 h-px bg-[var(--tp-border-default)]';
