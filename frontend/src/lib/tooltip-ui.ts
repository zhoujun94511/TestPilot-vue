import { cn } from '@/lib/utils';

/** 与 dropdown 浮层同级的 Tooltip 面板 */
export const tooltipContentClass = cn(
  'z-[1060] max-w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-[var(--tp-radius-md)]',
  'border border-[var(--tp-border-default)] bg-[var(--tp-bg-elevated)] px-3 py-2',
  'text-sm leading-snug text-[var(--tp-foreground)] shadow-[var(--tp-shadow-md)]',
  'duration-150 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0'
);
