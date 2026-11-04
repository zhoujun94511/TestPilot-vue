import { cva, type VariantProps } from 'class-variance-authority';
import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { cn } from '@/lib/utils';

/** 应用壳 grid（DefaultLayout 根节点） */
export function shellRootClass(options: { collapsed: boolean }) {
  const cols = options.collapsed
    ? 'grid-cols-[var(--tp-shell-sidebar-width-collapsed)_minmax(0,1fr)]'
    : 'grid-cols-[var(--tp-shell-sidebar-width)_minmax(0,1fr)]';

  return cn(
    'relative grid min-h-screen overflow-x-clip bg-[var(--tp-bg-page)] transition-[grid-template-columns] duration-200 ease-out',
    cols,
    'max-[1199px]:grid-cols-1',
    'before:pointer-events-none before:fixed before:inset-0 before:z-0 before:opacity-95 before:content-[""]',
    'before:bg-[radial-gradient(circle_at_top_right,color-mix(in_srgb,var(--tp-color-primary-600)_5%,transparent)_0,transparent_32%),radial-gradient(circle_at_18%_18%,color-mix(in_srgb,var(--tp-color-ai-600)_4%,transparent)_0,transparent_30%)]'
  );
}

export const shellSidebarBackdropClass =
  'fixed inset-x-0 bottom-0 top-[var(--tp-topbar-min-height)] z-[35] hidden bg-[color-mix(in_srgb,var(--tp-color-text-900)_42%,transparent)] backdrop-blur-[2px] max-[1199px]:block';

export function shellSidebarClass(mobileNavOpen: boolean) {
  return cn(
    'tp-shell-sidebar sticky top-0 z-30 flex h-screen min-h-0 flex-col gap-2 border-r border-[var(--tp-border-default)] bg-[color-mix(in_srgb,var(--tp-bg-surface)_92%,transparent)] px-3 py-4 backdrop-blur-md max-[1199px]:z-40',
    'max-[1199px]:fixed max-[1199px]:left-0 max-[1199px]:top-0 max-[1199px]:h-screen max-[1199px]:w-[min(var(--tp-shell-sidebar-width),88vw)] max-[1199px]:shadow-[var(--tp-shadow-lg)] max-[1199px]:transition-transform max-[1199px]:duration-200',
    mobileNavOpen ? 'max-[1199px]:translate-x-0' : 'max-[1199px]:-translate-x-[105%]'
  );
}

export function shellBrandHeaderClass(collapsed: boolean) {
  return cn(
    'flex gap-2 pb-[18px] pt-2.5',
    collapsed ? 'flex-col items-center px-2' : 'items-start justify-between px-3'
  );
}

export function shellBrandBlockClass(collapsed: boolean) {
  return cn('flex min-w-0 flex-1 items-center gap-3', collapsed && 'flex-none justify-center');
}

export const shellBrandTextClass = 'min-w-0 flex-1 overflow-hidden';

export const shellBrandMarkClass =
  'inline-flex h-10 w-10 items-center justify-center rounded-xl bg-transparent font-bold tracking-wider text-inherit shadow-none';

export const shellNavGroupClass = 'mt-2.5 first:mt-0 [&+&]:mt-[18px]';

/** 分组名保持常规字距。0.12em 的大写字距是给英文眉标用的，中文会显得字被撑开。 */
export const shellNavGroupTitleClass =
  'mb-2 px-3 text-[0.6875rem] font-medium leading-4 tracking-normal text-[var(--tp-color-text-500)]';

/** 略留水平余量，避免滚动容器裁切项右侧圆角 */
export const shellNavListClass = 'tp-shell-nav-list grid gap-1.5';

/** 侧栏主体：菜单过长时与 footer 一起滚动 */
export const shellSidebarBodyClass =
  'tp-subtle-scrollbar flex min-h-0 w-full flex-1 flex-col overflow-y-auto';

export const shellMainNavClass = 'min-w-0 w-full shrink-0';

/**
 * 个人设置 + 版权贴在侧栏底部。菜单不满一屏时整组沉底；超出时跟导航一起滚动。
 * pt-8 比分组间距（18px）更大，和个人设置上面的入口分开。
 */
export const shellSidebarDockClass = 'mt-auto flex w-full shrink-0 flex-col pt-8';

/** 与主导航项同一水平内缩，避免个人设置比上面的入口更宽 */
export const shellSidebarAccountTriggerClass = cn(
  'mx-1.5 mb-3 w-[calc(100%-0.75rem)] max-w-[calc(100%-0.75rem)] text-left',
  'data-[state=open]:border-[var(--tp-border-default)] data-[state=open]:bg-[var(--tp-bg-subtle)] data-[state=open]:text-[var(--tp-color-text-900)]'
);

export const shellSidebarFooterClass = cn(
  'shrink-0 border-t border-[var(--tp-border-default)] px-3 pb-4 pt-3'
);

export const shellSidebarCopyrightClass =
  'text-center text-[0.65rem] font-medium leading-snug text-[var(--tp-color-text-500)]';

const navItemVariants = cva(
  cn(
    'flex items-center gap-3 rounded-[var(--tp-radius-md)] border px-3 py-[11px] no-underline transition-[background-color,border-color,color,transform] duration-150',
    interactiveFocusRingClass
  ),
  {
    variants: {
      active: {
        true: 'tp-nav-item--active',
        false: ''
      },
      collapsed: {
        true: 'justify-center px-2.5',
        false: ''
      },
      /** 配置分类这类卡片行常显外框；主导航保持无框，避免侧栏变厚 */
      framed: {
        true: '',
        false: ''
      }
    },
    compoundVariants: [
      {
        active: false,
        framed: false,
        class: cn(
          'border-transparent bg-transparent text-[var(--tp-color-text-600)]',
          'hover:border-[var(--tp-border-default)] hover:bg-[var(--tp-bg-subtle)] hover:text-[var(--tp-color-text-900)]'
        )
      },
      {
        active: false,
        framed: true,
        class: cn(
          'border-[var(--tp-border-default)] border-l-[3px] border-l-[var(--tp-border-default)]',
          'bg-[var(--tp-bg-surface)] text-[var(--tp-color-text-600)]',
          'hover:border-[var(--tp-border-strong)] hover:border-l-[var(--tp-border-strong)]',
          'hover:bg-[var(--tp-bg-subtle)] hover:text-[var(--tp-color-text-900)]'
        )
      }
    ],
    defaultVariants: {
      active: false,
      collapsed: false,
      framed: false
    }
  }
);

export type NavItemClassOptions = VariantProps<typeof navItemVariants>;

export function navItemClass(options?: NavItemClassOptions) {
  return cn(navItemVariants(options));
}

const navItemIconVariants = cva(
  'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--tp-radius-sm)] text-[var(--tp-color-primary-600)]',
  {
    variants: {
      active: {
        true: 'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_16%,var(--tp-bg-subtle))]',
        false: 'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_8%,var(--tp-bg-subtle))]'
      }
    },
    defaultVariants: { active: false }
  }
);

export type NavItemIconClassOptions = VariantProps<typeof navItemIconVariants>;

export function navItemIconClass(options?: NavItemIconClassOptions) {
  return cn(navItemIconVariants(options));
}

/**
 * 13px、字重 400。微软雅黑没有 600，font-semibold 会被合成成粗体，侧栏中文会比图标和分组名重一截。
 * 选中态靠底色、左边线和文字颜色区分，不再靠加粗。
 */
export const navItemLabelClass =
  'min-w-0 flex-1 truncate text-[0.8125rem] font-normal leading-5 tracking-normal';

export const shellWorkspaceClass = 'relative z-0 min-w-0';

export const shellTopbarClass =
  'sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-[var(--tp-border-default)] bg-[color-mix(in_srgb,var(--tp-bg-page)_84%,transparent)] px-[var(--tp-content-padding)] py-2 backdrop-blur-[10px] max-[767px]:flex-wrap max-[767px]:gap-2 max-[767px]:px-4 max-[767px]:py-1.5';

export const shellTopbarLeftClass =
  'flex min-w-0 items-center gap-2 max-[767px]:w-full';

/** 窄屏顶栏操作换到标题下一行，避免把页标题挤成逐字换行 */
export const shellTopbarActionsClass =
  'flex shrink-0 flex-wrap items-center gap-2 max-[767px]:w-full max-[767px]:justify-end';

export const shellContentClass =
  'mx-auto max-w-[1440px] p-[var(--tp-content-padding)] max-[767px]:p-4';

/** 侧栏折叠按钮（品牌区旁，桌面常显；窄屏抽屉内亦可用） */
export const shellCollapseBtnClass = cva(
  cn(
    'inline-flex min-h-9 min-w-9 shrink-0 cursor-pointer items-center justify-center rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-2 text-[var(--tp-color-text-600)] transition-[background-color,border-color,color] duration-150 hover:border-[var(--tp-border-strong)] hover:bg-[var(--tp-accent)] hover:text-[var(--tp-color-text-900)]',
    interactiveFocusRingClass
  )
);

/** 顶栏图标按钮（语言/主题） */
export const topbarIconBtnClass = cva(
  cn(
    'inline-flex min-h-9 min-w-9 cursor-pointer items-center justify-center gap-1.5 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] p-1.5 text-[var(--tp-color-text-600)] transition-[background-color,border-color,color] duration-150 hover:border-[color-mix(in_srgb,var(--tp-color-primary-600)_24%,var(--tp-border-default))] hover:bg-[var(--tp-accent)] hover:text-[var(--tp-color-primary-600)]',
    interactiveFocusRingClass
  )
);

export const topbarLangBadgeClass = 'text-[10px] font-bold tracking-wider';

export const breadcrumbListClass =
  'm-0 flex list-none flex-wrap items-center gap-1 p-0';

export const breadcrumbItemClass = 'inline-flex min-w-0 items-center gap-1';

export const breadcrumbLinkClass = cn(
  'rounded-[var(--tp-radius-sm)] text-[0.8125rem] font-medium text-[var(--tp-color-text-500)] no-underline transition-colors duration-150 hover:text-[var(--tp-color-primary-600)]',
  interactiveFocusRingClass
);

export const breadcrumbCurrentClass =
  'text-sm font-bold leading-snug text-[var(--tp-color-text-900)]';

export const breadcrumbSepClass = 'shrink-0 text-[var(--tp-color-text-500)]';

export const languageSwitcherClass = 'inline-flex gap-2';
