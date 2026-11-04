import type { KnowledgeFileRecord } from '@/api/knowledge';

/** 用例优先级 → TpTag variant */
export function casePriorityTagVariant(priority: string | undefined) {
  switch (priority) {
    case 'P0':
      return 'danger';
    case 'P1':
      return 'warning';
    case 'P2':
      return 'info';
    case 'P3':
    case 'P4':
      return 'neutral';
    default:
      return 'neutral';
  }
}

/** 用例状态 → TpTag variant */
export function caseStatusTagVariant(status: string | undefined) {
  switch (status) {
    case 'active':
      return 'success';
    case 'draft':
      return 'neutral';
    case 'deprecated':
      return 'danger';
    default:
      return 'neutral';
  }
}

/** 文档 / 分析状态 → TpTag variant */
export function documentStatusTagVariant(status?: string) {
  const key = (status || '').toLowerCase();
  if (['analyzed', 'active', 'ready', 'done'].includes(key)) return 'success';
  if (['analyzing', 'processing', 'pending'].includes(key)) return 'warning';
  if (['failed', 'error'].includes(key)) return 'danger';
  return 'neutral';
}

/** 知识库文件状态 → TpTag variant */
export function knowledgeFileStatusTagVariant(file: KnowledgeFileRecord) {
  if (file.is_duplicate) return 'warning';
  switch ((file.status || 'active').toLowerCase()) {
    case 'active':
      return 'success';
    case 'processing':
      return 'info';
    case 'archived':
      return 'neutral';
    case 'failed':
      return 'danger';
    default:
      return 'neutral';
  }
}
