import { cn } from '@/lib/utils';

/** 预览正文块（滚动由 FormSideDrawer body 承担，与用例编辑抽屉一致） */
export const previewDrawerContentClass = cn(
  'm-0 block min-w-0 whitespace-pre-wrap break-words rounded-[var(--tp-radius-md)] bg-muted p-3',
  'text-[0.8125rem] leading-[1.55] text-[var(--tp-color-text-600)]'
);
