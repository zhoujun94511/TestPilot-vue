import { cn } from '@/lib/utils';

/** 页面根：块级流式排布，避免给每个子块同 z-index 导致叠层发糊 */
export const pageRootClass = 'relative flex flex-col gap-[var(--tp-page-block-gap)]';

/** 大面板内分区（KPI / 筛选 / 表格），替代再套一层 PagePanel */
export const pageSectionDivideClass =
  'border-t border-[var(--tp-border-default)] pt-[var(--tp-space-4)] mt-[var(--tp-space-4)]';

/** 子页壳最小高度（原 `.tp-page-shell`） */
export const pageShellClass = 'min-h-[var(--tp-page-shell-min-height)]';

export const pageShellCompactClass = 'min-h-0';

/** 原 `.tp-container-fluid` */
export const pageContainerFluidClass = 'w-full px-0';

/** 全宽容器 + 纵向内边距 + 页面根/壳（Shell 布局页常用） */
export function pageFluidShellSectionClass(options?: { compact?: boolean }) {
  return cn(
    pageContainerFluidClass,
    'py-3',
    'relative flex flex-col gap-2',
    options?.compact ? pageShellCompactClass : pageShellClass
  );
}

/** 12 列网格（原 `.tp-row` + `.tp-g-3`） */
export const grid12Class = 'grid grid-cols-12 gap-4 [&>*]:min-w-0';

export const grid12StretchClass = cn(grid12Class, 'items-stretch');

export const colSpan12 = 'col-span-12';

export const colSpan12Lg4 = 'col-span-12 lg:col-span-4';

export const colSpan12Lg8 = 'col-span-12 lg:col-span-8';

export const colSpan12Lg2 = 'col-span-12 lg:col-span-2';

export const grid12ItemsEndClass = cn(grid12Class, 'items-end');

export const colSpan12Xl3 = 'col-span-12 xl:col-span-3';

export const colSpan12Xl9 = 'col-span-12 xl:col-span-9';

export const colSpan12Md6 = 'col-span-12 md:col-span-6';

export const colSpan12Xl6 = 'col-span-12 xl:col-span-6';

/** 原 `.tp-col-md-6` + `.tp-col-xxl-3`（1400px） */
export const colSpan12Md6Min1400_3 = 'col-span-12 md:col-span-6 min-[1400px]:col-span-3';

export const colSpan12Md4 = 'col-span-12 md:col-span-4';

/** 原 `.tp-col-xxl-5` / `.tp-col-xxl-7`（1400px） */
export const colSpan12Min1400_5 = 'col-span-12 min-[1400px]:col-span-5';

export const colSpan12Min1400_7 = 'col-span-12 min-[1400px]:col-span-7';

/** 原 `.tp-mb-3`（16px） */
export const sectionStackGapClass = 'mb-4';

export const casesDistributionItemClass =
  'h-full rounded-none border-0 bg-transparent p-4 shadow-none';

/** 页面根稳定钩子（测试 / 主题扩展；无对应 CSS 规则） */
export const pageMarkerDashboard = 'tp-dashboard-page';
export const pageMarkerCases = 'tp-cases-page';
export const pageMarkerDocuments = 'tp-documents-page';
export const pageMarkerDocumentsHistory = 'tp-documents-history-page';
export const pageMarkerDocumentsUpload = 'tp-documents-upload-page';
export const pageMarkerKnowledge = 'tp-knowledge-page';
export const pageMarkerKnowledgeSearch = 'tp-knowledge-search-page';
export const pageMarkerKnowledgeUpload = 'tp-knowledge-upload-page';
export const pageMarkerChat = 'tp-chat-page';
export const pageMarkerConfig = 'tp-config-page';

export function pageRootMarkedClass(marker: string) {
  return cn(pageRootClass, marker);
}

export function pageFluidShellMarkedClass(
  marker: string,
  options?: { compact?: boolean }
) {
  return cn(pageFluidShellSectionClass(options), marker);
}
