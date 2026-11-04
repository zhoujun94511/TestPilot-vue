import { cn } from '@/lib/utils';
import { grid12Class } from '@/lib/page-layout-ui';

/** PagePanel 文件列表区（滚动条样式见 KnowledgeView scoped） */
export const KNOWLEDGE_FILES_PANEL_MARKER = 'knowledge-files-panel';

export const knowledgeLayoutClass = cn(grid12Class, 'min-[1200px]:items-stretch');

export const knowledgeMainColClass = cn(
  'min-w-0',
  'min-[1200px]:flex min-[1200px]:h-full min-[1200px]:min-h-0 min-[1200px]:flex-col'
);

export const knowledgeFilterStickyClass =
  'sticky top-[72px] z-30 max-[1199px]:top-3';

export const knowledgeWorkspaceClass =
  'grid w-full grid-cols-1 gap-3 min-[1200px]:items-stretch';

export const knowledgePanelShellClass =
  'box-border flex min-h-0 flex-col overflow-hidden';

export const knowledgePanelBodyClass =
  'min-h-0 flex-1 overflow-auto [scrollbar-gutter:stable]';

export const knowledgeFilesPanelClass = cn(
  knowledgePanelShellClass,
  KNOWLEDGE_FILES_PANEL_MARKER
);

export const knowledgePanelFooterClass =
  'mt-2 flex min-h-[42px] items-end justify-end';

export {
  statsSummaryMetricClass as knowledgeStatsMetricClass,
  statsSummaryPanelClass as knowledgeStatsPanelClass
} from '@/lib/stats-ui';

export const knowledgeFilesPanelBodyClass = cn(
  knowledgePanelBodyClass,
  'min-w-0 p-4',
  '[&_.base-table-block]:flex [&_.base-table-block]:h-full',
  '[&_.base-table-block]:min-h-0 [&_.base-table-block]:flex-col',
  '[&_.base-table-wrap]:min-h-0 [&_.base-table-wrap]:flex-1',
  '[&_.base-table-wrap]:overflow-auto [&_.base-table-wrap]:[scrollbar-gutter:stable_both-edges]'
);
