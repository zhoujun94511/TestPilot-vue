import { cva } from 'class-variance-authority';
import { CONFIG_SECTION_PANEL_MARKER } from '@/lib/config-ui';
import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { surfacePanelClass } from '@/lib/surface-ui';
import { cn } from '@/lib/utils';

export const panelShellClass = cva(surfacePanelClass, {
  variants: {
    flat: { true: 'shadow-none', false: '' },
    aside: { true: 'h-full p-[var(--tp-space-4)]', false: '' }
  },
  defaultVariants: {
    flat: false,
    aside: false
  }
});

/** 配置分区自带边框/背景（configSectionPanelClass），不再叠 surfacePanelClass */
export const configSectionPanelShellClass = 'min-w-0 p-0';

export const panelHeaderClass =
  'flex items-start justify-between gap-[var(--tp-space-3)] px-[var(--tp-space-4)] pt-[var(--tp-space-4)] max-[767px]:flex-col';

export const panelTitleClass = 'text-[0.9375rem] font-bold text-foreground';

export const panelSubtitleClass =
  'mt-1 text-[0.8125rem] leading-snug text-muted-foreground';

export const panelConfigTitleClass =
  'text-[0.98rem] font-bold text-[var(--tp-color-text-900)]';

export const panelConfigSubtitleClass =
  'mt-1 text-sm text-[var(--tp-color-text-500)]';

export const panelActionsClass =
  'flex flex-wrap justify-end gap-[var(--tp-space-2)] max-[767px]:justify-start';

export const panelBodyPaddedClass = 'min-w-0 p-[var(--tp-space-4)]';

export const panelBodyPaddedBelowHeaderClass =
  'min-w-0 px-[var(--tp-space-4)] pb-[var(--tp-space-4)] pt-[var(--tp-space-3)]';

export function panelBodyClass(options: { padded: boolean; hasHeader: boolean }) {
  if (!options.padded) return '';
  return options.hasHeader ? panelBodyPaddedBelowHeaderClass : panelBodyPaddedClass;
}

export const sidebarMenuClass = 'flex min-h-0 flex-col gap-[var(--tp-space-3)]';

export const sidebarMenuHeaderClass =
  'flex items-start justify-between gap-[var(--tp-space-2)]';

export const sidebarMenuTitleClass = panelTitleClass;

export const sidebarMenuSubtitleClass = panelSubtitleClass;

export const sidebarMenuBodyClass =
  'grid min-h-0 gap-1.5 overflow-auto pb-[var(--tp-space-2)]';

export const pageTabsNavClass = cn(
  'mt-0 inline-flex w-fit max-w-full flex-wrap gap-1 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-muted)] p-1',
  'mb-0',
  'dark:bg-[color-mix(in_srgb,var(--tp-bg-subtle)_80%,var(--tp-bg-surface))]'
);

export const pageTabItemClass = cva(
  cn(
    'inline-flex items-center justify-center rounded-[calc(var(--tp-radius-md)-2px)] px-3.5 py-[7px] text-[0.8125rem] font-semibold text-muted-foreground no-underline transition-[background-color,color,box-shadow] duration-150 hover:bg-[color-mix(in_srgb,var(--tp-bg-surface)_70%,transparent)] hover:text-foreground',
    interactiveFocusRingClass
  ),
  {
    variants: {
      active: {
        true:
          'border border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] text-foreground shadow-[var(--tp-shadow-sm)] dark:border-[var(--tp-border-strong)]',
        false: ''
      }
    },
    defaultVariants: { active: false }
  }
);

/** 检测 PagePanel 上的配置分区标记（配置页标题字号） */
export function attrsIncludeConfigSection(classAttr: unknown): boolean {
  if (!classAttr) return false;
  const marker = CONFIG_SECTION_PANEL_MARKER;
  if (typeof classAttr === 'string') {
    return classAttr.includes(marker);
  }
  if (Array.isArray(classAttr)) {
    return classAttr.some((part) => attrsIncludeConfigSection(part));
  }
  return false;
}
