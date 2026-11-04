import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/** PagePanel 上标记配置分区，用于 config 标题 typography */
export const CONFIG_SECTION_PANEL_MARKER = 'config-section-panel';

const providerAccentKeys = ['openai', 'deepseek', 'ollama', 'gemini', 'qwen'] as const;
export type ConfigProviderAccent = (typeof providerAccentKeys)[number] | 'none';

export const configSectionPanelClass = cva(
  `${CONFIG_SECTION_PANEL_MARKER} min-w-0 rounded-[var(--tp-radius-lg)] border border-[var(--tp-border-default)] bg-[color-mix(in_srgb,var(--tp-bg-surface)_96%,var(--tp-color-primary-600)_4%)]`,
  {
    variants: {
      scope: {
        shared:
          'bg-[color-mix(in_srgb,var(--tp-bg-surface)_98%,var(--tp-color-text-900)_2%)]',
        provider: 'shadow-[var(--tp-shadow-sm)]'
      },
      active: {
        true: 'border-[color-mix(in_srgb,var(--tp-color-primary-600)_28%,var(--tp-border-default))]',
        false: ''
      },
      providerAccent: {
        none: '',
        openai: 'border-l-4 border-l-[var(--tp-color-ai-600)]',
        deepseek: 'border-l-4 border-l-[var(--tp-color-primary-600)]',
        ollama: 'border-l-4 border-l-[var(--tp-color-success-600)]',
        gemini: 'border-l-4 border-l-[var(--tp-color-info-600)]',
        qwen: 'border-l-4 border-l-[var(--tp-color-warning-600)]'
      }
    },
    defaultVariants: {
      scope: 'provider',
      active: false,
      providerAccent: 'none'
    }
  }
);

export type ConfigSectionPanelOptions = VariantProps<typeof configSectionPanelClass>;

export function resolveConfigProviderAccent(key: string): ConfigProviderAccent {
  const normalized = key.trim().toLowerCase();
  if ((providerAccentKeys as readonly string[]).includes(normalized)) {
    return normalized as ConfigProviderAccent;
  }
  return 'none';
}

export const configSectionMetaClass = 'flex flex-wrap justify-end gap-2';

export const configFooterClass = cn(
  'sticky bottom-0 z-[2] mt-[var(--tp-space-4)] border-t border-[var(--tp-border-default)] pt-[var(--tp-space-3)]',
  'bg-[color-mix(in_srgb,var(--tp-bg-surface)_92%,transparent)] backdrop-blur-sm'
);

export const configSidebarStickyClass = 'sticky top-5';

export const configCategoryItemClass = 'w-full justify-between text-left';

export const configFormStackClass = 'grid min-w-0 gap-3.5';

export const configFormFieldFootClass = 'mt-2';

export const configFormHelpTextClass =
  'block text-[0.78rem] text-[var(--tp-color-text-500)]';

export const configFormErrorTextClass =
  'block text-[0.78rem] text-[var(--tp-color-danger-600)]';

export const configMetaClass = 'text-sm text-[var(--tp-color-text-500)]';

export const configToolbarHintClass = configMetaClass;

export const configToolbarStatusClass = configMetaClass;

export const configOverviewClass = 'grid gap-[18px]';

export const configOverviewHeadClass =
  'flex flex-wrap items-start justify-between gap-3.5';

export const configOverviewEyebrowClass =
  'mb-1 text-[0.72rem] font-bold uppercase tracking-[0.12em] text-[var(--tp-color-text-500)]';

export const configOverviewMetricsClass = 'flex flex-wrap gap-2';

export const configOverviewCountClass = 'ml-1.5 opacity-80';

export const configProviderGridClass = 'grid gap-3.5';

/** 侧栏「最近配置变更」虚拟分类 id（非后端 category） */
export const CONFIG_AUDIT_CATEGORY_ID = 'audit_trail';

export function isConfigAuditCategoryId(categoryId: string) {
  return categoryId === CONFIG_AUDIT_CATEGORY_ID;
}

/** 审计日志条数超过该值时列表区域可纵向滚动 */
export const CONFIG_AUDIT_LOG_SCROLL_THRESHOLD = 5;

export function configAuditLogListClass(enableScroll: boolean) {
  return cn(
    'space-y-2 text-sm',
    enableScroll &&
      'tp-subtle-scrollbar max-h-[min(24rem,45vh)] min-h-0 overflow-y-auto overscroll-y-contain [scrollbar-width:thin] pr-0.5'
  );
}
