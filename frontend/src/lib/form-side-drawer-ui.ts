import { cn } from '@/lib/utils';

/** 侧栏宽度与遮罩右缘对齐（编辑 / 预览共用） */
export const formSideDrawerWidthClass =
  'w-[min(42vw,760px)] max-[1199px]:w-[min(92vw,760px)] min-w-[440px] max-[1199px]:min-w-0';

/** 顶边跟实测顶栏底对齐，底边贴视口，不再额外留 100px / 3rem 的缝 */
export const formSideDrawerPanelClass = cn(
  'pointer-events-auto fixed right-0 bottom-0 z-[1101] flex min-h-0 flex-col overflow-hidden',
  formSideDrawerWidthClass,
  'top-[var(--tp-preview-top-offset,var(--tp-topbar-min-height))]',
  'border border-border border-b-0 border-r-0 border-t-0 bg-background text-foreground',
  'shadow-[-8px_0_22px_rgba(0,0,0,0.16)]',
  'rounded-none'
);

/** 仅覆盖左侧工作区，不挡住右侧抽屉，避免滚轮被透明遮罩吃掉 */
export const formSideDrawerBackdropClass = cn(
  'pointer-events-auto fixed z-[1100] bg-transparent',
  'top-[var(--tp-preview-top-offset,100px)] bottom-0 left-0',
  'right-[min(42vw,760px)] max-[1199px]:right-[min(92vw,760px)]'
);

export const formSideDrawerBodyClass = cn(
  'tp-subtle-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-y-contain [scrollbar-width:thin]',
  'touch-pan-y px-4 py-4'
);
