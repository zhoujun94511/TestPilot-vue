import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { toDisplayValue } from '@/composables/chat/chatDisplayUtils';

export function usePendingExperimentalAction() {
  const { t } = useI18n();

  const pendingActionExecutionId = ref('');
  const pendingActionPlan = ref<Record<string, unknown> | null>(null);
  const pendingActionPreview = ref<Record<string, unknown> | null>(null);
  const deleteActionConfirmText = ref('');

  function resetPendingAction() {
    pendingActionExecutionId.value = '';
    pendingActionPlan.value = null;
    pendingActionPreview.value = null;
    deleteActionConfirmText.value = '';
  }

  function restorePendingAction(items: Array<{ content?: string }>) {
    resetPendingAction();
    for (let index = items.length - 1; index >= 0; index -= 1) {
      const content = String(items[index]?.content || '');
      const idMatch = content.match(/执行ID:\s*`([^`]+)`/);
      if (!idMatch) continue;
      const statusMatch = content.match(/"status"\s*:\s*"([^"]+)"/);
      if (statusMatch?.[1] === 'needs_confirmation') {
        pendingActionExecutionId.value = idMatch[1];
        const toolMatch = content.match(/"tool"\s*:\s*"([^"]+)"/);
        const toolName = toolMatch?.[1] || '';
        pendingActionPlan.value = {
          tool_name: toolName,
          risk_level: toolName === 'rule_skeleton_cases' ? 'medium' : 'low',
          requires_confirmation: true
        };
      }
      return;
    }
  }

  function applyPendingFromSendResult(result: {
    status?: string;
    execution_id?: string;
    action_plan?: Record<string, unknown> | null;
    tool_results?: Record<string, unknown> | null;
  }) {
    const actionStatus = String(result.status || '');
    if (actionStatus === 'needs_confirmation' && result.execution_id) {
      pendingActionExecutionId.value = String(result.execution_id);
      pendingActionPlan.value = result.action_plan ?? null;
      pendingActionPreview.value = result.tool_results ?? null;
    }
  }

  function localizeActionFieldKey(key: string) {
    const keyMap: Record<string, string> = {
      success: t('chat.action.field.success'),
      message: t('chat.action.field.message'),
      case_id: t('chat.action.field.caseId'),
      title: t('chat.action.field.title'),
      status: t('chat.action.field.status'),
      dry_run: t('chat.action.field.dryRun'),
      total: t('chat.action.field.total'),
      count: t('chat.action.field.count')
    };
    return keyMap[key] || key;
  }

  const pendingActionSummary = computed(() => {
    const plan = pendingActionPlan.value || {};
    return {
      intent: toDisplayValue(plan.intent),
      toolName: toDisplayValue(plan.tool_name),
      riskLevel: toDisplayValue(plan.risk_level === '-' ? 'low' : plan.risk_level)
    };
  });

  const pendingActionRiskVariant = computed<'danger' | 'warning' | 'neutral'>(() => {
    const riskLevel = String(pendingActionPlan.value?.risk_level || 'low').toLowerCase();
    if (riskLevel === 'high') return 'danger';
    if (riskLevel === 'medium') return 'warning';
    return 'neutral';
  });

  const showHighRiskHint = computed(() => pendingActionRiskVariant.value === 'danger');

  const requireDeleteKeywordConfirm = computed(() => pendingActionRiskVariant.value === 'danger');

  const canConfirmPendingAction = computed(() => {
    if (!requireDeleteKeywordConfirm.value) return true;
    return deleteActionConfirmText.value.toUpperCase() === 'DELETE';
  });

  const deleteConfirmSatisfied = computed(() => canConfirmPendingAction.value);

  const pendingActionArgsEntries = computed(() => {
    const args = pendingActionPlan.value?.args;
    if (!args || typeof args !== 'object' || Array.isArray(args)) return [] as Array<{ key: string; value: string }>;
    return Object.entries(args)
      .slice(0, 10)
      .map(([key, value]) => ({ key: localizeActionFieldKey(key), value: toDisplayValue(value) }));
  });

  const pendingActionPreviewSummary = computed(() => {
    const preview = pendingActionPreview.value || {};
    const toolName = String(pendingActionPlan.value?.tool_name || '').trim();
    const keys = toolName === 'rule_skeleton_cases'
      ? ['success', 'message', 'count', 'dry_run']
      : ['success', 'message', 'dry_run'];
    const entries: Array<{ key: string; value: string }> = [];
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(preview, key)) {
        entries.push({ key: localizeActionFieldKey(key), value: toDisplayValue(preview[key]) });
      }
    }
    if (!entries.length) {
      const fallbackKeys = Object.keys(preview).slice(0, 8);
      for (const key of fallbackKeys) {
        entries.push({ key: localizeActionFieldKey(key), value: toDisplayValue(preview[key]) });
      }
    }
    return entries;
  });

  return {
    pendingActionExecutionId,
    pendingActionPlan,
    pendingActionPreview,
    deleteActionConfirmText,
    resetPendingAction,
    restorePendingAction,
    applyPendingFromSendResult,
    pendingActionSummary,
    pendingActionRiskVariant,
    showHighRiskHint,
    requireDeleteKeywordConfirm,
    canConfirmPendingAction,
    deleteConfirmSatisfied,
    pendingActionArgsEntries,
    pendingActionPreviewSummary
  };
}
