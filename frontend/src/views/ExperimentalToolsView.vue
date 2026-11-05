<template>
  <section :class="pageRootClass">
    <BaseState
      v-if="featureUnavailable"
      variant="empty"
      :title="t('experimentalToolsPage.disabled.title')"
      :message="t('experimentalToolsPage.disabled.message')"
    />
    <template v-else>
      <PagePanel
        :title="t('experimentalToolsPage.page.title')"
        :subtitle="t('experimentalToolsPage.page.subtitle')"
      >
        <form class="grid gap-4" novalidate @submit.prevent="runTool">
          <div :class="grid12ItemsEndClass">
            <div :class="colSpan12Lg8">
              <TpInput
                v-model="experimentalToolId"
                as="select"
                input-id="exp-tool-select"
                :label="t('chat.experimentalTools.toolLabel')"
                :options="toolOptions"
                :disabled="toolRunning || Boolean(pendingActionExecutionId)"
              />
            </div>
            <div :class="[colSpan12Lg4, 'flex h-10 items-center']">
              <TpTag v-if="toolsCatalog[experimentalToolId]" :variant="riskVariant">
                {{ riskLabel(toolsCatalog[experimentalToolId]) }}
              </TpTag>
            </div>
          </div>

          <p v-if="toolDesc(experimentalToolId)" :class="[helpTextClass, '-mt-2']">
            {{ toolDesc(experimentalToolId) }}
          </p>

          <div v-if="currentToolDef?.fields.length" :class="grid12Class">
            <template v-for="field in currentToolDef.fields" :key="field.key">
              <div v-if="field.type === 'boolean'" :class="[colSpan12, 'flex items-center']">
                <TpSwitch
                  :model-value="Boolean(toolFields[field.key])"
                  @update:model-value="setToolField(field.key, $event)"
                  :switch-id="`exp-tool-${field.key}`"
                  :label="fieldLabel(field.key)"
                  :disabled="toolRunning"
                />
              </div>
              <div v-else-if="field.type === 'requirement'" :class="fieldColClass(field.type)">
                <TpInput
                  v-model="toolFields[field.key]"
                  as="select"
                  :input-id="`exp-tool-${field.key}`"
                  :label="fieldLabel(field.key)"
                  :options="requirementOptions"
                  :required="field.required"
                  :placeholder="requirementPlaceholder(field.placeholderKey ?? field.key)"
                  :disabled="toolRunning || Boolean(pendingActionExecutionId) || requirementsLoading"
                />
                <p v-if="requirementsHint" :class="[helpTextClass, 'mt-1']">{{ requirementsHint }}</p>
              </div>
              <div v-else :class="fieldColClass(field.type)">
                <TpInput
                  v-model="toolFields[field.key]"
                  :input-id="`exp-tool-${field.key}`"
                  :label="fieldLabel(field.key)"
                  :as="field.type === 'textarea' ? 'textarea' : 'input'"
                  :type="field.type === 'number' ? 'number' : 'text'"
                  :rows="field.type === 'textarea' ? 6 : undefined"
                  :min="field.min"
                  :max="field.max"
                  :required="field.required"
                  :placeholder="fieldPlaceholder(field.placeholderKey ?? field.key)"
                  :disabled="toolRunning || Boolean(pendingActionExecutionId)"
                />
              </div>
            </template>
          </div>

          <div
            v-if="pendingActionExecutionId"
            :class="pendingPanelClass"
            role="alert"
          >
            <div :class="dataTitleClass">{{ t('chat.action.pendingTitle') }}</div>
            <p v-if="showHighRiskHint" :class="[helpTextClass, 'mt-1 text-[var(--tp-notice-warning-fg-emphasis)]']">
              {{ t('chat.action.highRiskHint') }}
            </p>
            <p :class="[helpTextClass, 'mt-1']">
              {{ t('chat.action.executionId') }}: <code>{{ pendingActionExecutionId }}</code>
            </p>
            <div v-if="requireDeleteKeywordConfirm" class="mt-3 max-w-sm">
              <TpInput
                v-model="deleteActionConfirmText"
                input-id="exp-delete-confirm"
                :label="t('chat.action.deleteConfirmLabel')"
                :placeholder="t('chat.action.deleteConfirmPlaceholder')"
                :disabled="confirmLoading"
              />
            </div>
            <div class="mt-3 flex flex-wrap justify-end gap-2">
              <TpButton variant="ghost" :disabled="confirmLoading" @click="cancelPending">
                {{ t('chat.actions.cancelAction') }}
              </TpButton>
              <TpButton
                :variant="showHighRiskHint ? 'danger' : 'primary'"
                :loading="confirmLoading"
                :disabled="confirmLoading || !canConfirmPendingAction"
                @click="confirmPending"
              >
                {{ confirmButtonLabel }}
              </TpButton>
            </div>
          </div>

          <div v-else class="flex justify-end">
            <TpButton type="submit" :loading="toolRunning" :disabled="toolRunning">
              {{ toolRunning ? t('chat.experimentalTools.running') : t('chat.experimentalTools.run') }}
            </TpButton>
          </div>
        </form>
      </PagePanel>

      <PagePanel>
        <template #header>
          <div :class="panelTitleClass">{{ t('experimentalToolsPage.results.title') }}</div>
        </template>
        <template v-if="resultTable || resultText" #actions>
          <TpButton
            v-if="coverageGaps && !pendingActionExecutionId"
            variant="secondary"
            size="sm"
            :disabled="toolRunning"
            @click="openSkeletonFromGaps"
          >
            {{ t('experimentalToolsPage.results.skeletonFromGaps', { count: coverageGaps.gaps.length }) }}
          </TpButton>
          <TpButton variant="ghost" size="sm" :disabled="Boolean(pendingActionExecutionId)" @click="clearResult">
            {{ t('experimentalToolsPage.results.clear') }}
          </TpButton>
        </template>

        <BaseState
          v-if="!resultTable && !resultText"
          variant="empty"
          :title="t('experimentalToolsPage.results.empty')"
        />
        <PagedScrollTable
          v-else-if="resultTable"
          :title="resultTable.title"
          :columns="resultColumns"
          :rows="resultTable.rows"
          :row-key="resultTable.rowKey"
          :empty-title="resultTable.emptyTitle"
        >
          <template v-if="resultLink" #actions>
            <RouterLink :to="resultLink.to" :class="resultLinkClass">
              {{ resultLink.label }}
            </RouterLink>
          </template>
        </PagedScrollTable>
        <div v-else :class="resultTextPaneClass">
          <ChatMessageContent :content="resultText" />
        </div>
      </PagePanel>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useI18n } from 'vue-i18n';
import PagePanel from '@/components/common/PagePanel.vue';
import PagedScrollTable from '@/components/common/PagedScrollTable.vue';
import BaseState from '@/components/common/BaseState.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpSwitch from '@/components/ui/base/TpSwitch.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import ChatMessageContent from '@/components/chat/ChatMessageContent.vue';
import {
  cancelExperimentalAction,
  confirmExperimentalAction,
  createChatSession
} from '@/api/chat';
import { executeExperimentalAction, fetchExperimentalActionsHealth } from '@/api/experimentalActions';
import { getDocumentRequirements } from '@/api/documents';
import { resolveExperimentalToolErrorMessage } from '@/composables/chat/chatSendErrors';
import { usePendingExperimentalAction } from '@/composables/usePendingExperimentalAction';
import { usePageNotifier } from '@/composables/usePageNotifier';
import {
  EXPERIMENTAL_TOOL_DEFS,
  buildExperimentalToolArgs,
  defaultFieldValuesForTool,
  getExperimentalToolDef,
  toolComposerContextFieldKeys,
  validateExperimentalToolForm,
  type ExperimentalToolFieldType
} from '@/config/experimentalTools';
import { formatActionResultContent, extractExperimentalToolTable } from '@/lib/experimentalToolResultMarkdown';
import { asRecord } from '@/composables/chat/chatDisplayUtils';
import { helpTextClass } from '@/lib/field-control';
import type { BaseTableColumn } from '@/components/common/BaseTable.vue';
import {
  colSpan12,
  colSpan12Lg4,
  colSpan12Lg8,
  colSpan12Md6,
  grid12Class,
  grid12ItemsEndClass,
  pageRootMarkedClass
} from '@/lib/page-layout-ui';
import { dataTitleClass } from '@/lib/page-typography';
import { panelTitleClass } from '@/lib/panel-ui';
import { tableBodyScrollClass, tableWrap } from '@/lib/table-ui';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';

const EXP_SESSION_KEY = 'testpilot_experimental_tools_session_id';
const REQUIREMENT_OPTION_LIMIT = 200;
const REQUIREMENT_TITLE_MAX = 40;
/** 切换工具时沿用的长文本字段（需求描述 / 文档正文） */
const LONG_TEXT_FIELD_KEYS = ['requirement_text', 'content'];

const pendingPanelClass =
  'rounded-[var(--tp-radius-md)] border border-[color-mix(in_srgb,var(--tp-color-warning-500)_35%,var(--tp-border-default))] bg-[color-mix(in_srgb,var(--tp-color-warning-500)_8%,var(--tp-bg-surface))] p-4';

const { t } = useI18n();
const route = useRoute();
const { showNotice } = usePageNotifier();

const pageRootClass = pageRootMarkedClass('experimental-tools');

const featureUnavailable = ref(false);
const sessionId = ref('');
const experimentalToolId = ref(EXPERIMENTAL_TOOL_DEFS[0].id);
const toolFields = ref<Record<string, string | number | boolean>>(defaultFieldValuesForTool(EXPERIMENTAL_TOOL_DEFS[0].id));
const toolRunning = ref(false);
const confirmLoading = ref(false);
const toolsCatalog = ref<Record<string, string>>({});

interface ToolTableResult {
  kind: 'cases';
  title: string;
  emptyTitle: string;
  rowKey: string;
  rows: Record<string, unknown>[];
}

const resultTable = ref<ToolTableResult | null>(null);
const resultText = ref('');
const resultLink = ref<{ to: string; label: string } | null>(null);
const coverageGaps = ref<{ requirementId: string; gaps: string[] } | null>(null);

const resultTextPaneClass = cn(tableWrap(), tableBodyScrollClass, 'p-4');
const resultLinkClass =
  'inline-flex h-8 items-center rounded-md px-3 text-xs font-semibold text-[var(--tp-color-primary-700)] hover:bg-accent';

const {
  pendingActionExecutionId,
  pendingActionPlan,
  resetPendingAction,
  applyPendingFromSendResult,
  showHighRiskHint,
  requireDeleteKeywordConfirm,
  canConfirmPendingAction,
  deleteActionConfirmText
} = usePendingExperimentalAction();

const toolOrder = new Map(EXPERIMENTAL_TOOL_DEFS.map((def, index) => [def.id, index]));

const currentToolDef = computed(() => getExperimentalToolDef(experimentalToolId.value));

interface RequirementOption {
  value: string;
  label: string;
}

const requirementList = ref<RequirementOption[]>([]);
const requirementsTotal = ref(0);
const requirementsLoading = ref(false);
const requirementsLoaded = ref(false);
const requirementsFailed = ref(false);

const requirementOptions = computed<RequirementOption[]>(() => {
  const selected = String(toolFields.value.requirement_id ?? '').trim();
  if (!selected || requirementList.value.some((item) => item.value === selected)) {
    return requirementList.value;
  }
  return [{ value: selected, label: selected }, ...requirementList.value];
});

const requirementsHint = computed(() => {
  if (requirementsFailed.value) return t('experimentalToolsPage.requirements.loadFailed');
  if (!requirementsLoaded.value) return '';
  if (!requirementList.value.length) return t('experimentalToolsPage.requirements.empty');
  if (requirementsTotal.value > requirementList.value.length) {
    return t('experimentalToolsPage.requirements.truncated', {
      shown: requirementList.value.length,
      total: requirementsTotal.value
    });
  }
  return '';
});

function requirementPlaceholder(key: string) {
  if (requirementsLoading.value) return t('experimentalToolsPage.requirements.loading');
  return fieldPlaceholder(key);
}

function requirementLabel(title: string, reqId: string) {
  const text = title.trim() || reqId;
  const short = text.length > REQUIREMENT_TITLE_MAX ? `${text.slice(0, REQUIREMENT_TITLE_MAX)}…` : text;
  return `${short}（${reqId}）`;
}

async function loadRequirementOptions() {
  if (requirementsLoaded.value || requirementsLoading.value) return;
  requirementsLoading.value = true;
  requirementsFailed.value = false;
  try {
    const result = await getDocumentRequirements({ page: 1, per_page: REQUIREMENT_OPTION_LIMIT });
    requirementList.value = result.requirements
      .filter((item) => item.req_id)
      .map((item) => ({ value: item.req_id, label: requirementLabel(item.title || '', item.req_id) }));
    requirementsTotal.value = result.total;
    requirementsLoaded.value = true;
  } catch {
    requirementsFailed.value = true;
  } finally {
    requirementsLoading.value = false;
  }
}

watch(
  currentToolDef,
  (def) => {
    if (!featureUnavailable.value && def?.fields.some((field) => field.type === 'requirement')) {
      void loadRequirementOptions();
    }
  },
  { immediate: true }
);

const toolOptions = computed(() => {
  const registered = Object.keys(toolsCatalog.value);
  const ids = registered.length ? registered : [experimentalToolId.value];
  return [...ids]
    .sort((a, b) => (toolOrder.get(a) ?? Number.MAX_SAFE_INTEGER) - (toolOrder.get(b) ?? Number.MAX_SAFE_INTEGER))
    .map((id) => ({ value: id, label: toolLabel(id) }));
});

const riskVariant = computed<'danger' | 'warning' | 'neutral'>(() => {
  const risk = String(toolsCatalog.value[experimentalToolId.value] || 'low').toLowerCase();
  if (risk === 'high') return 'danger';
  if (risk === 'medium') return 'warning';
  return 'neutral';
});

function fieldColClass(type: ExperimentalToolFieldType) {
  return type === 'textarea' ? colSpan12 : colSpan12Md6;
}

function setToolField(key: string, value: string | number | boolean) {
  toolFields.value = { ...toolFields.value, [key]: value };
}

function translatedOr(key: string, fallback: string) {
  const label = t(key);
  return label !== key ? label : fallback;
}

function toolLabel(toolId: string) {
  return translatedOr(`chat.experimentalTools.tools.${toolId}`, toolId);
}

function fieldLabel(fieldKey: string) {
  return translatedOr(`chat.experimentalTools.fields.${fieldKey}`, fieldKey);
}

function toolDesc(toolId: string) {
  return translatedOr(`chat.experimentalTools.toolDesc.${toolId}`, '');
}

function fieldPlaceholder(fieldKey: string) {
  return translatedOr(`chat.experimentalTools.placeholders.${fieldKey}`, '');
}

function riskLabel(riskRaw: string | undefined) {
  const normalized = String(riskRaw || 'low').trim().toLowerCase();
  return translatedOr(`chat.experimentalTools.risk.${normalized}`, normalized);
}

const resultColumns = computed<BaseTableColumn[]>(() => [
  { key: 'case_id', label: t('cases.table.columns.caseId'), width: '220px' },
  { key: 'title', label: t('cases.table.columns.title') },
  { key: 'priority', label: t('cases.table.columns.priority'), width: '90px' },
  { key: 'status', label: t('cases.table.columns.status'), width: '100px' },
  { key: 'module', label: t('cases.table.columns.module'), width: '140px' }
]);

const confirmButtonLabel = computed(() =>
  String(pendingActionPlan.value?.tool_name || '') === 'rule_skeleton_cases'
    ? t('experimentalToolsPage.results.confirmSave')
    : t('chat.actions.confirmAction')
);

function clearResult() {
  resultTable.value = null;
  resultText.value = '';
  resultLink.value = null;
  coverageGaps.value = null;
}

function readCoverageGaps(toolId: string, output: Record<string, unknown> | null) {
  if (toolId !== 'ac_coverage_review' || !output || output.success === false) return null;
  const gaps = Array.isArray(output.gaps) ? output.gaps.map(String).filter(Boolean) : [];
  const requirement = asRecord(output.requirement);
  const requirementId = String(requirement?.req_id || '').trim();
  return gaps.length && requirementId ? { requirementId, gaps } : null;
}

function showToolResult(toolId: string, message: string, output: Record<string, unknown> | null) {
  coverageGaps.value = readCoverageGaps(toolId, output);
  const table = extractExperimentalToolTable(toolId, output);
  if (!table) {
    resultTable.value = null;
    resultLink.value = null;
    resultText.value = formatActionResultContent(t, message, toolId, output);
    return;
  }
  const hids = table.rows
    .map((row) => String(row.case_id || '').trim())
    .filter((id) => id && id !== '-')
    .slice(0, 12)
    .join(',');
  resultLink.value = {
    label: t('experimentalToolsPage.results.openCases'),
    to: hids ? `/cases/manage?from=generate&hids=${encodeURIComponent(hids)}&at=action_chat` : '/cases/manage'
  };
  resultText.value = '';
  resultTable.value = {
    kind: table.kind,
    rows: table.rows,
    title: t('cases.table.title'),
    emptyTitle: t('cases.table.empty'),
    rowKey: 'case_id'
  };
}

async function openSkeletonFromGaps() {
  const target = coverageGaps.value;
  if (!target) return;
  experimentalToolId.value = 'rule_skeleton_cases';
  await nextTick();
  toolFields.value = {
    ...defaultFieldValuesForTool('rule_skeleton_cases'),
    requirement_text: target.gaps.join('\n'),
    requirement_id: target.requirementId
  };
  showNotice('info', t('experimentalToolsPage.results.skeletonFromGapsHint'));
}

async function ensureSession() {
  try {
    let id = localStorage.getItem(EXP_SESSION_KEY) || '';
    if (!id) {
      const created = await createChatSession({ title: t('experimentalToolsPage.page.title') });
      id = created.session_id || created.session?.session_id || '';
      if (id) localStorage.setItem(EXP_SESSION_KEY, id);
    }
    sessionId.value = id;
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('chat.message.loadSessionsFailed')));
  }
}

async function loadHealth() {
  try {
    const health = await fetchExperimentalActionsHealth();
    toolsCatalog.value = health.tools;
    featureUnavailable.value = false;
    if (!health.tools[experimentalToolId.value] && toolOptions.value.length) {
      experimentalToolId.value = toolOptions.value[0].value;
    }
  } catch {
    toolsCatalog.value = {};
    featureUnavailable.value = true;
  }
}

function longTextValue(values: Record<string, string | number | boolean>) {
  for (const key of LONG_TEXT_FIELD_KEYS) {
    const text = String(values[key] ?? '').trim();
    if (text) return text;
  }
  return '';
}

watch(experimentalToolId, (next) => {
  const carried = longTextValue(toolFields.value);
  const values = defaultFieldValuesForTool(next);
  if (carried) {
    for (const key of LONG_TEXT_FIELD_KEYS) {
      if (key in values) values[key] = carried;
    }
  }
  toolFields.value = values;
});

async function applyRouteQuery() {
  const tool = String(route.query.tool || '').trim();
  const prefill = String(route.query.prefill || '').trim();
  if (tool && getExperimentalToolDef(tool)) {
    experimentalToolId.value = tool;
    await nextTick();
  }
  if (!prefill) return;
  const next = { ...toolFields.value };
  for (const key of toolComposerContextFieldKeys(experimentalToolId.value)) {
    next[key] = prefill;
  }
  toolFields.value = next;
}

async function runTool() {
  if (toolRunning.value) return;
  await ensureSession();
  if (!sessionId.value) return;
  const toolId = experimentalToolId.value;
  if (validateExperimentalToolForm(toolId, toolFields.value)) {
    showNotice('warning', t('chat.experimentalTools.validationFailed'));
    return;
  }
  try {
    toolRunning.value = true;
    resetPendingAction();
    const result = await executeExperimentalAction({
      query: t('chat.experimentalTools.queryAudit', { tool: toolId }),
      session_id: sessionId.value,
      tool_name: toolId,
      args: buildExperimentalToolArgs(toolId, toolFields.value),
      require_confirmation: true,
      metadata: { send_source: 'experimental_tool_page' }
    });
    const toolName = String(result.plan?.tool_name || toolId);
    if (result.status === 'needs_confirmation' && result.execution_id) {
      applyPendingFromSendResult({
        status: result.status,
        execution_id: result.execution_id,
        action_plan: (result.plan as Record<string, unknown> | null) ?? null,
        tool_results: result.tool_output ?? null
      });
      showToolResult(toolName, result.message || '', (result.tool_output as Record<string, unknown> | null) ?? null);
      return;
    }
    showToolResult(toolName, result.message || '', (result.tool_output as Record<string, unknown> | null) ?? null);
    if (result.status === 'skipped') {
      showNotice('warning', t('chat.experimentalTools.runSkipped'));
    } else if (result.success) {
      showNotice('success', t('chat.experimentalTools.runSuccess'));
    } else {
      showNotice('danger', t('chat.experimentalTools.runFailed'));
    }
  } catch (error) {
    showNotice('danger', resolveExperimentalToolErrorMessage(error, t));
  } finally {
    toolRunning.value = false;
  }
}

async function confirmPending() {
  if (!pendingActionExecutionId.value || confirmLoading.value) return;
  if (!canConfirmPendingAction.value) {
    showNotice('warning', t('chat.action.deleteConfirmInvalid'));
    return;
  }
  try {
    confirmLoading.value = true;
    const confirmMetadata: Record<string, unknown> = {};
    if (requireDeleteKeywordConfirm.value) {
      confirmMetadata.confirmation_text = deleteActionConfirmText.value;
      confirmMetadata.secondary_confirmed = canConfirmPendingAction.value;
    }
    const resp = await confirmExperimentalAction(pendingActionExecutionId.value, confirmMetadata);
    const toolName = String(pendingActionPlan.value?.tool_name || '');
    showToolResult(
      toolName,
      String(resp.message || t('chat.toolMarkdown.actionConfirmed')),
      asRecord(resp.tool_output)
    );
    resetPendingAction();
    showNotice('success', t('chat.experimentalTools.runSuccess'));
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('chat.message.sendFailed')));
  } finally {
    confirmLoading.value = false;
  }
}

async function cancelPending() {
  if (!pendingActionExecutionId.value || confirmLoading.value) return;
  const toolName = String(pendingActionPlan.value?.tool_name || '');
  try {
    confirmLoading.value = true;
    await cancelExperimentalAction(pendingActionExecutionId.value, 'cancel_from_experimental_tools_page');
    const message = t('chat.toolMarkdown.actionCancelled');
    showToolResult(toolName, message, null);
    resetPendingAction();
    showNotice('warning', message);
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('chat.message.sendFailed')));
  } finally {
    confirmLoading.value = false;
  }
}

onMounted(async () => {
  await loadHealth();
  if (!featureUnavailable.value) {
    await applyRouteQuery();
  }
});
</script>
