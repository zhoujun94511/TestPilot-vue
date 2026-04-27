<template>
  <section class="tp-documents-page">
    <div v-if="notice" class="tp-risk-block tp-mb-3" :class="noticeClass">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-3">
        <div class="tp-flex-grow-1">{{ notice.message }}</div>
        <div class="tp-flex tp-align-center tp-gap-2">
          <TpButton
            v-if="notice.actionLabel && notice.onAction"
            variant="secondary"
            size="sm"
            @click="handleNoticeAction"
          >
            {{ notice.actionLabel }}
          </TpButton>
          <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="notice = null">
            {{ t('common.actions.close') }}
          </TpButton>
        </div>
      </div>
    </div>

    <div class="tp-doc-page-actions tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-gap-2 tp-justify-end">
        <TpButton variant="secondary" :loading="listLoading" @click="handleRefresh">
          {{ t('documents.actions.refresh') }}
        </TpButton>
        <TpButton
          variant="danger"
          :disabled="analyzeLoading || !selectedDocumentKeys.length"
          @click="handleDeleteSelectedDocuments"
        >
          {{ t('documents.actions.deleteDocuments') }}
        </TpButton>
        <TpButton variant="primary" :loading="generating" :disabled="generating || !canGenerateCases" @click="handleGenerateCases">
          {{ generating ? t('documents.actions.generating') : t('documents.actions.generateCases') }}
        </TpButton>
        <TpButton
          variant="secondary"
          :loading="exportingRequirements"
          :disabled="exportingRequirements || !analysisRequirements.length"
          @click="handleExportRequirements"
        >
          {{ exportingRequirements ? t('documents.actions.exportingRequirements') : t('documents.actions.exportRequirements') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-row tp-g-3">
      <div class="tp-col-12">
        <div class="tp-surface tp-p-3 tp-mb-3">
          <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
            <div>
              <div class="tp-card__title">{{ t('documents.filters.title') }}</div>
              <div class="tp-card__subtitle">
                <span v-if="selectedDocument">
                  {{ t('documents.result.selected') }}: {{ resolveDocumentLabel(selectedDocument) }}
                </span>
                <span v-else>{{ t('documents.message.selectDocumentFirst') }}</span>
                <span v-if="selectedDocumentKeys.length" class="tp-ml-2">
                  · {{ t('documents.result.selectedDocumentsCount', { count: selectedDocumentKeys.length }) }}
                </span>
              </div>
            </div>
            <div class="tp-small" style="color: var(--tp-color-text-500)">{{ paginationText }}</div>
          </div>

          <form class="tp-row tp-g-3 tp-align-end" @submit.prevent="handleSearch">
            <div class="tp-col-12 tp-col-lg-6">
              <label class="tp-form-label">{{ t('documents.filters.keywordLabel') }}</label>
              <input
                v-model.trim="filters.search"
                type="search"
                class="tp-input"
                :placeholder="t('documents.filters.keywordPlaceholder')"
              />
            </div>

            <div class="tp-col-12 tp-col-lg-4">
              <label class="tp-form-label">{{ t('documents.filters.analysisTypeLabel') }}</label>
              <select v-model="filters.analysisType" class="tp-select">
                <option v-for="option in analysisTypeOptions" :key="`filter-${option.value}`" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="tp-col-12 tp-col-lg-2 tp-grid">
              <TpButton :loading="listLoading" @click="handleSearch">
                {{ t('documents.filters.apply') }}
              </TpButton>
            </div>
          </form>
        </div>

        <div class="tp-surface tp-p-3 tp-mb-3">
          <div v-if="listError" class="tp-mb-3">
            <BaseState
              variant="error"
              :title="t('common.status.error')"
              :message="listError"
              :retry-text="t('common.actions.retry')"
              @retry="handleRefresh"
            />
          </div>

          <BaseTable
            v-else
            :columns="documentColumns"
            :data="documents"
            :row-class="resolveDocumentRowClass"
            :loading="listLoading"
            :loading-title="t('documents.table.loading')"
            :empty-title="t('documents.table.empty')"
            :empty-message="''"
            :selectable="true"
            :selected-keys="selectedDocumentKeys"
            row-key="document_key"
            @update:selectedKeys="handleDocumentSelectionUpdate"
            @toggleAll="handleDocumentToggleAll"
            @rowClick="selectDocument"
          >
            <template #cell-name="{ row }">
              <div class="tp-data-title">{{ resolveDocumentLabel(row as DocumentRecord) }}</div>
              <div v-if="(row as DocumentRecord).description" class="tp-data-subtitle text-truncate" style="max-width: 24rem">
                {{ (row as DocumentRecord).description }}
              </div>
            </template>
            <template #cell-type="{ row }">
              {{ resolveFileTypeLabel((row as DocumentRecord).file_type) }}
            </template>
            <template #cell-status="{ row }">
              <TpTag :variant="statusTagVariant((row as DocumentRecord).status || (row as DocumentRecord).analysis_status)">
                {{ resolveStatusLabel((row as DocumentRecord).status || (row as DocumentRecord).analysis_status) }}
              </TpTag>
            </template>
            <template #cell-updatedAt="{ row }">
              {{ formatDateTime((row as DocumentRecord).updated_time || (row as DocumentRecord).created_time) }}
            </template>
            <template #cell-actions="{ row }">
              <div class="tp-flex tp-justify-end tp-gap-2">
                <TpButton
                  v-if="canViewAnalysisResult(row as DocumentRecord)"
                  variant="secondary"
                  size="sm"
                  @click.stop="openHistoryResultsForDocument(row as DocumentRecord)"
                >
                  {{ t('documents.actions.viewResult') }}
                </TpButton>
                <TpButton
                  v-if="isAnalyzingStatus((row as DocumentRecord).status || (row as DocumentRecord).analysis_status)"
                  variant="secondary"
                  size="sm"
                  :disabled="true"
                >
                  {{ t('documents.actions.analyzing') }}
                </TpButton>
                <TpButton variant="ai" size="sm" @click.stop="analyzeDocumentRow(row as DocumentRecord)">
                  {{ t('common.actions.analyze') }}
                </TpButton>
                <TpButton variant="secondary" size="sm" @click.stop="previewDocumentRow(row as DocumentRecord)">
                  {{ t('documents.actions.preview') }}
                </TpButton>
                <TpButton
                  v-if="canViewAnalysisResult(row as DocumentRecord)"
                  variant="secondary"
                  size="sm"
                  @click.stop="reanalyzeDocumentRow(row as DocumentRecord)"
                >
                  {{ t('documents.actions.reanalyze') }}
                </TpButton>
                <TpButton variant="danger" size="sm" @click.stop="handleDeleteSingleDocument(row as DocumentRecord)">
                  {{ t('common.actions.delete') }}
                </TpButton>
              </div>
            </template>
          </BaseTable>
          <div v-if="pagination.pages > 1" class="tp-flex tp-flex-wrap tp-justify-between tp-align-center tp-gap-2 tp-mt-3">
            <div class="tp-small" style="color: var(--tp-color-text-500)">{{ paginationText }}</div>
            <TpPager
              :page="pagination.page"
              :per-page="pagination.per_page"
              :total="pagination.total"
              :pages="pagination.pages"
              :has-prev="Boolean(pagination.has_prev)"
              :has-next="Boolean(pagination.has_next)"
              :previous-text="t('common.actions.previous')"
              :next-text="t('common.actions.next')"
              @change="changePage"
            />
          </div>
        </div>

        <div v-if="showAnalysisPanel || analyzeLoading || analysisError || currentAnalysis" ref="analysisPanelRef" class="tp-surface tp-p-3">
          <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
            <div>
              <div class="tp-card__title">{{ t('documents.analysis.title') }}</div>
              <div class="tp-card__subtitle">
                {{ selectedDocument ? `${t('documents.analysis.sourceDocument')}: ${resolveDocumentLabel(selectedDocument)}` : t('documents.analysis.empty') }}
              </div>
            </div>
            <TpButton size="sm" :loading="generating" :disabled="generating || !analysisRequirements.length" @click="handleGenerateCases">
              {{ t('documents.actions.generateCases') }}
            </TpButton>
          </div>

          <BaseState
            v-if="analyzeLoading && !currentAnalysis"
            variant="loading"
            :title="t('documents.analysis.loading')"
          />
          <BaseState
            v-else-if="analysisError"
            variant="error"
            :title="t('documents.analysis.error')"
            :message="analysisError"
            :retry-text="t('common.actions.retry')"
            @retry="handleAnalyzeSelected"
          />
          <BaseState
            v-else-if="!currentAnalysis"
            variant="empty"
            :title="t('documents.analysis.empty')"
            :message="t('documents.message.selectDocumentFirst')"
          />

          <template v-else>
            <AiResultCard
              :title="analysisTitle"
              :subtitle="analysisSubtitle"
              :confidence="analysisConfidence"
              :confidence-label="analysisConfidenceLabel"
            >
              <template #summary>
                <div class="tp-state__message tp-text-start">{{ analysisSummaryText }}</div>
              </template>

              <template #metrics>
                <div class="tp-row tp-g-3">
                  <div v-for="card in summaryCards" :key="card.key" class="tp-col-12 tp-col-md-6 tp-col-xxl-3">
                    <TpCard>
                      <div class="tp-kpi-label">{{ card.label }}</div>
                      <div class="tp-kpi-value">{{ card.value }}</div>
                      <div v-if="card.hint" class="tp-kpi-hint">{{ card.hint }}</div>
                    </TpCard>
                  </div>
                </div>
              </template>

              <template #evidence>
                <div v-if="analysisRequirements.length" class="tp-grid tp-gap-2">
                  <div class="tp-flex tp-justify-between tp-align-center">
                    <label class="tp-toggle">
                      <input
                        class="tp-check"
                        type="checkbox"
                        :checked="allRequirementsSelected"
                        @change="toggleSelectAllRequirements(($event.target as HTMLInputElement).checked)"
                      />
                      <span class="tp-small">{{ t('documents.actions.selectAllRequirements') }}</span>
                    </label>
                    <TpButton
                      variant="danger"
                      size="sm"
                      :disabled="!selectedRequirementIds.length"
                      @click="handleDeleteSelectedRequirements"
                    >
                      {{ t('documents.actions.deleteRequirements') }}
                    </TpButton>
                  </div>
                  <div
                    v-for="item in pagedAnalysisRequirements"
                    :key="item.req_id"
                    class="tp-surface__body tp-p-0 tp-analysis-requirement-item"
                    :class="resolveRequirementItemClass(item.req_id)"
                    :data-req-id="item.req_id"
                  >
                    <div class="tp-flex tp-justify-between tp-align-start tp-gap-2">
                      <label class="tp-toggle">
                        <input
                          class="tp-check"
                          type="checkbox"
                          :checked="selectedRequirementIds.includes(item.req_id)"
                          @change="toggleRequirementSelection(item.req_id, ($event.target as HTMLInputElement).checked)"
                        />
                        <span class="tp-small">{{ item.req_id }}</span>
                      </label>
                      <TpButton variant="danger" size="sm" @click="handleDeleteSingleRequirement(item.req_id)">
                        {{ t('common.actions.delete') }}
                      </TpButton>
                    </div>
                    <div class="tp-data-title tp-mt-2">{{ item.title }}</div>
                    <div class="tp-data-subtitle">{{ item.content }}</div>
                  </div>
                  <TpPager
                    class="tp-mt-2"
                    :page="analysisRequirementPagination.page"
                    :per-page="analysisRequirementPagination.per_page"
                    :total="analysisRequirementPagination.total"
                    :pages="analysisRequirementPagination.pages"
                    :has-prev="Boolean(analysisRequirementPagination.has_prev)"
                    :has-next="Boolean(analysisRequirementPagination.has_next)"
                    :previous-text="t('common.actions.previous')"
                    :next-text="t('common.actions.next')"
                    @change="changeAnalysisRequirementPage"
                  />
                </div>
                <BaseState
                  v-else
                  variant="empty"
                  :title="t('documents.analysis.noRequirements')"
                  :message="currentAnalysis?.message || ''"
                />
              </template>

              <template #raw>
                <pre class="tp-raw-block">{{ analysisRawText }}</pre>
              </template>
            </AiResultCard>
          </template>
        </div>

        <PreviewDrawer
          :visible="previewPanelVisible"
          :title="t('documents.preview.title')"
          :subtitle="previewDocumentLabel"
          :meta-line="previewMetaLine"
          :content="previewDisplayContent"
          :loading="previewLoading"
          :error="previewError"
          :loading-title="t('documents.preview.loading')"
          :empty-title="t('documents.preview.empty')"
          :error-title="t('common.status.error')"
          :close-text="t('common.actions.close')"
          :copy-text="t('common.actions.copy')"
          :copied-text="t('common.actions.copied')"
          :copyable="true"
          @copied="handlePreviewCopied"
          @copyFailed="handlePreviewCopyFailed"
          @close="closePreviewPanel"
        />

      </div>
    </div>
    <ConfirmDialog
      v-model="deleteConfirmVisible"
      :title="deleteConfirmTitle"
      :message="deleteConfirmMessage"
      :confirm-text="deleteConfirmButtonText"
      :cancel-text="t('common.actions.cancel')"
      :confirm-variant="deleteConfirmVariant"
      @confirm="runDeleteConfirmAction"
      @cancel="clearDeleteConfirm"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import PreviewDrawer from '@/components/common/PreviewDrawer.vue';
import AiResultCard from '@/components/ui/AiResultCard.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAiResult } from '@/composables/useAiResult';
import {
  analyzeDocument,
  deleteDocument,
  deleteRequirement,
  exportRequirementsExcel,
  getDocumentPreview,
  getDocumentRequirements,
  generateCasesFromAnalysis,
  listDocuments,
  reanalyzeDocument,
  type DocumentAnalysisResult,
  type DocumentAnalysisType,
  type DocumentRecord,
  type DocumentPreviewResult,
  type DocumentRequirementRecord
} from '@/api/documents';

interface NoticeState {
  type: 'success' | 'danger' | 'warning' | 'info';
  message: string;
  actionLabel?: string;
  onAction?: () => void | Promise<void>;
}

interface SelectOption {
  value: DocumentAnalysisType;
  label: string;
}

const { t, locale } = useI18n();
const route = useRoute();
const router = useRouter();
const documents = ref<DocumentRecord[]>([]);
const currentAnalysis = ref<DocumentAnalysisResult | null>(null);
const selectedDocumentKey = ref<string>('');
const listLoading = ref(false);
const analyzeLoading = ref(false);
const generating = ref(false);
const exportingRequirements = ref(false);
const listError = ref('');
const analysisError = ref('');
const notice = ref<NoticeState | null>(null);
const noticeTimer = ref<number | null>(null);
const analysisPanelRef = ref<HTMLElement | null>(null);
const selectedDocumentKeys = ref<Array<string | number>>([]);
const selectedDocumentRecordMap = ref<Record<string, DocumentRecord>>({});
const selectedRequirementIds = ref<string[]>([]);
const showAnalysisPanel = ref(false);
const currentAnalysisDocumentKey = ref('');
const currentPreview = ref<DocumentPreviewResult | null>(null);
const previewLoading = ref(false);
const previewError = ref('');
const previewPanelVisible = ref(false);
const deleteConfirmVisible = ref(false);
const deleteConfirmTitle = ref('');
const deleteConfirmMessage = ref('');
const deleteConfirmAction = ref<null | (() => Promise<void>)>(null);
const deleteConfirmButtonText = ref(t('common.actions.delete'));
const deleteConfirmVariant = ref<'primary' | 'danger' | 'warning'>('danger');
const highlightDocumentKeys = ref<Set<string>>(new Set());
const highlightRequirementIds = ref<Set<string>>(new Set());
const highlightDocumentTimer = ref<number | null>(null);
const highlightRequirementTimer = ref<number | null>(null);

const filters = reactive({
  search: '',
  analysisType: 'requirements' as DocumentAnalysisType,
  page: 1,
  per_page: 10
});

const pagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

const analysisTypeOptions = computed<SelectOption[]>(() => [
  { value: 'requirements', label: t('enums.documents.analysisType.requirements') },
  { value: 'test_points', label: t('enums.documents.analysisType.test_points') },
  { value: 'business_rules', label: t('enums.documents.analysisType.business_rules') },
  { value: 'comprehensive', label: t('enums.documents.analysisType.comprehensive') }
]);

const documentColumns = computed<BaseTableColumn[]>(() => [
  { key: 'name', label: t('documents.table.columns.name') },
  { key: 'type', label: t('documents.table.columns.type'), width: '120px' },
  { key: 'status', label: t('documents.table.columns.status'), width: '120px' },
  { key: 'updatedAt', label: t('documents.table.columns.updatedAt'), width: '180px' },
  { key: 'actions', label: t('documents.table.columns.actions'), width: '320px', headerClass: 'text-end', cellClass: 'text-end' }
]);

const requirementColumns = computed<BaseTableColumn[]>(() => [
  { key: 'req_id', label: t('documents.requirement.id'), width: '120px' },
  { key: 'title', label: t('documents.requirement.title') },
  { key: 'type', label: t('documents.requirement.type'), width: '120px' },
  { key: 'priority', label: t('documents.requirement.priority'), width: '120px' },
  { key: 'category', label: t('documents.requirement.category'), width: '120px' }
]);

const selectedDocument = computed(() => {
  return documents.value.find((doc) => resolveDocumentKey(doc) === selectedDocumentKey.value) || documents.value[0] || null;
});

const analysisRequirements = computed<DocumentRequirementRecord[]>(() => currentAnalysis.value?.requirements || []);
const selectedDocuments = computed(() =>
  selectedDocumentKeys.value
    .map((key) => selectedDocumentRecordMap.value[String(key)])
    .filter((doc): doc is DocumentRecord => Boolean(doc))
);
const selectedAnalyzedDocuments = computed(() =>
  selectedDocuments.value.filter((doc) => canViewAnalysisResult(doc))
);
const canGenerateCases = computed(() =>
  analysisRequirements.value.length > 0 || selectedAnalyzedDocuments.value.length > 0
);
const allRequirementsSelected = computed(
  () => analysisRequirements.value.length > 0
    && analysisRequirements.value.every((item) => selectedRequirementIds.value.includes(item.req_id))
);
const analysisRequirementPage = ref(1);
const analysisRequirementsPerPage = 5;
const analysisRequirementPagination = computed(() => {
  const total = analysisRequirements.value.length;
  const pages = total > 0 ? Math.ceil(total / analysisRequirementsPerPage) : 0;
  return {
    page: analysisRequirementPage.value,
    per_page: analysisRequirementsPerPage,
    total,
    pages,
    has_prev: analysisRequirementPage.value > 1,
    has_next: analysisRequirementPage.value < pages
  };
});
const pagedAnalysisRequirements = computed<DocumentRequirementRecord[]>(() => {
  const start = (analysisRequirementPage.value - 1) * analysisRequirementsPerPage;
  return analysisRequirements.value.slice(start, start + analysisRequirementsPerPage);
});
const analysisAi = useAiResult(currentAnalysis);

const summaryCards = computed(() => {
  const summary = currentAnalysis.value?.summary;
  const requirements = analysisRequirements.value;
  const countsByType = requirements.reduce<Record<string, number>>((acc, item) => {
    const key = item.type || 'unknown';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const countsByPriority = requirements.reduce<Record<string, number>>((acc, item) => {
    const key = item.priority || 'unknown';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  return [
    {
      key: 'requirements',
      label: t('documents.result.requirementsCount'),
      value: summary?.requirements_count ?? requirements.length,
      hint: t('documents.analysis.summaryTitle')
    },
    {
      key: 'test_points',
      label: t('documents.result.testPointsCount'),
      value: summary?.test_points_count ?? countsByType.functional ?? countsByType.test_point ?? 0,
      hint: t('documents.analysis.summaryTitle')
    },
    {
      key: 'business_rules',
      label: t('documents.result.businessRulesCount'),
      value: summary?.business_rules_count ?? countsByType.business ?? countsByType.business_rule ?? 0,
      hint: t('documents.analysis.summaryTitle')
    },
    {
      key: 'total',
      label: t('documents.result.totalCount'),
      value: summary?.total_count ?? requirements.length,
      hint: t('common.status.empty')
    }
  ];
});

const analysisTitle = computed(() => {
  return selectedDocument.value ? `${t('documents.analysis.title')} - ${resolveDocumentLabel(selectedDocument.value)}` : t('documents.analysis.title');
});

const analysisSubtitle = computed(() => {
  return currentAnalysis.value?.analysis_type ? t('ai.typePrefix', { value: String(currentAnalysis.value.analysis_type) }) : t('documents.analysis.summaryTitle');
});

const analysisSummaryText = computed(() => {
  if (currentAnalysis.value?.message) return currentAnalysis.value.message;
  return t('ai.summary');
});

const analysisConfidence = computed(() => analysisAi.value.confidence);
const analysisConfidenceLabel = computed(() => analysisAi.value.confidenceLabel);

const analysisRawText = computed(() => JSON.stringify(currentAnalysis.value?.raw || currentAnalysis.value, null, 2));

const paginationText = computed(() => {
  if (!pagination.value.pages) {
    return t('common.status.empty');
  }
  return t('documents.pagination.pageInfo', {
    page: pagination.value.page,
    pages: pagination.value.pages
  });
});

const previewDocumentLabel = computed(() => {
  if (currentPreview.value?.filename) return currentPreview.value.filename;
  if (selectedDocument.value) return resolveDocumentLabel(selectedDocument.value);
  return t('documents.preview.empty');
});

const previewMetaLine = computed(() => {
  if (!currentPreview.value) return '';
  const meta = t('documents.preview.meta', {
    type: currentPreview.value.file_type || '-',
    size: formatBytes(currentPreview.value.file_size)
  });
  if (currentPreview.value.is_truncated) {
    return `${meta} · ${t('documents.preview.truncated')}`;
  }
  return meta;
});

const previewDisplayContent = computed(() => {
  const preview = currentPreview.value;
  if (!preview) return '-';
  return formatPreviewContent(preview.content, preview.content_type);
});

const noticeClass = computed(() => ({
  'tp-risk-block--info': notice.value?.type === 'info',
  'tp-risk-block--danger': notice.value?.type === 'danger',
  'tp-risk-block--warning': notice.value?.type === 'warning',
  'tp-risk-block--success': notice.value?.type === 'success'
}));

watch(analysisRequirements, () => {
  analysisRequirementPage.value = 1;
  selectedRequirementIds.value = selectedRequirementIds.value.filter((reqId) =>
    analysisRequirements.value.some((item) => item.req_id === reqId)
  );
});

function clearNotice() {
  if (noticeTimer.value) {
    window.clearTimeout(noticeTimer.value);
    noticeTimer.value = null;
  }
}

function showNotice(
  type: NoticeState['type'],
  message: string,
  timeout = 4500,
  options?: { actionLabel?: string; onAction?: () => void | Promise<void> }
) {
  clearNotice();
  notice.value = {
    type,
    message,
    actionLabel: options?.actionLabel,
    onAction: options?.onAction
  };
  if (timeout > 0) {
    noticeTimer.value = window.setTimeout(() => {
      notice.value = null;
      noticeTimer.value = null;
    }, timeout);
  }
}

async function handleNoticeAction() {
  const action = notice.value?.onAction;
  if (!action) return;
  await action();
  notice.value = null;
}

async function scrollToAnalysisPanel() {
  await nextTick();
  analysisPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function openAnalysisForDocument(doc: DocumentRecord) {
  const nextKey = resolveDocumentKey(doc);
  selectedDocumentKey.value = nextKey;
  showAnalysisPanel.value = true;

  const hasCurrent = currentAnalysisDocumentKey.value === nextKey && !!currentAnalysis.value;
  if (!hasCurrent) {
    currentAnalysis.value = null;
    analysisError.value = '';
    selectedRequirementIds.value = [];
  }

  if (!hasCurrent) {
    analyzeLoading.value = true;
    try {
      const response = await getDocumentRequirements({
        page: 1,
        per_page: 200,
        source_file: doc.filename || resolveDocumentLabel(doc)
      });
      if (response.requirements.length > 0) {
        const requirements = response.requirements;
        const testPoints = requirements.filter((item) => {
          const type = String(item.type || '').toLowerCase();
          return type === 'functional' || type === 'test_point';
        });
        const businessRules = requirements.filter((item) => {
          const type = String(item.type || '').toLowerCase();
          return type === 'business' || type === 'business_rule';
        });
        currentAnalysis.value = {
          success: true,
          message: t('documents.message.resultLoadedFromHistory'),
          analysis_type: 'requirements',
          requirements,
          test_points: testPoints,
          business_rules: businessRules,
          saved_requirements: requirements,
          summary: {
            requirements_count: requirements.length,
            test_points_count: testPoints.length,
            business_rules_count: businessRules.length,
            total_count: requirements.length
          }
        };
        currentAnalysisDocumentKey.value = nextKey;
      } else {
        showNotice('info', t('documents.message.resultNotReady'));
      }
    } catch (error) {
      analysisError.value = error instanceof Error ? error.message : t('documents.message.loadAnalysisFailed');
      showNotice('danger', analysisError.value);
    } finally {
      analyzeLoading.value = false;
    }
  }
  await scrollToAnalysisPanel();
}

async function openHistoryResultsForDocument(doc: DocumentRecord) {
  const source = resolveDocumentLabel(doc);
  await router.push({
    name: 'documents-history',
    query: source ? { source } : undefined
  });
}

function resolveDocumentKey(doc: DocumentRecord) {
  return doc.document_key || doc.relative_path || doc.file_path || String(doc.id);
}

function resolveDocumentLabel(doc: DocumentRecord) {
  return doc.file_name || doc.filename || t('documents.table.empty');
}

function resolveAnalyzePath(doc: DocumentRecord) {
  if (doc.analysis_path) return doc.analysis_path;
  if (doc.file_path) return doc.file_path;
  if (doc.filename) return `documents/${doc.filename}`;
  if (doc.relative_path) return `documents/${doc.relative_path}`;
  return String(doc.id);
}

function changeAnalysisRequirementPage(page: number) {
  if (page < 1 || page > (analysisRequirementPagination.value.pages || 1)) return;
  analysisRequirementPage.value = page;
}

function resolveReanalyzeId(doc: DocumentRecord) {
  return doc.filename || doc.relative_path || doc.file_path?.split('/').pop() || String(doc.id);
}

function resolveFileTypeLabel(fileType?: string) {
  const key = (fileType || 'unknown').toLowerCase();
  return t(`enums.documents.fileType.${key}`) || key;
}

function resolveStatusLabel(status?: string) {
  const key = (status || 'unknown').toLowerCase();
  return t(`enums.documents.status.${key}`) || key;
}

function isAnalyzingStatus(status?: string) {
  const key = String(status || '').toLowerCase();
  return ['analyzing', 'processing', 'pending'].includes(key);
}

function canViewAnalysisResult(doc: DocumentRecord) {
  const status = String(doc.status || doc.analysis_status || '').toLowerCase();
  const hasCount = Number(doc.requirements_count || 0) > 0;
  return status === 'analyzed' || status === 'done' || hasCount;
}

function resolveRequirementTypeLabel(type?: string) {
  const key = (type || 'functional').toLowerCase();
  if (key === 'functional' || key === 'test_point') return t('enums.documents.analysisType.test_points');
  if (key === 'business' || key === 'business_rule') return t('enums.documents.analysisType.business_rules');
  return key;
}

function resolvePriorityLabel(priority?: string) {
  const value = String(priority || '').trim().toLowerCase();
  if (value === 'p0' || value === 'critical') return 'P0';
  if (value === 'high' || value === 'p1') return 'P1';
  if (value === 'medium' || value === 'normal' || value === 'p2' || !value) return 'P2';
  if (value === 'low' || value === 'p3') return 'P3';
  return String(priority || '-').toUpperCase();
}

function statusTagVariant(status?: string) {
  const key = (status || '').toLowerCase();
  if (['analyzed', 'active', 'ready', 'done'].includes(key)) return 'success';
  if (['analyzing', 'processing', 'pending'].includes(key)) return 'warning';
  if (['failed', 'error'].includes(key)) return 'danger';
  return 'neutral';
}

function formatBytes(value?: number) {
  const bytes = Number(value ?? 0);
  if (!bytes) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDateTime(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}

function formatPreviewContent(content?: string, contentType?: string) {
  const raw = String(content || '').trim();
  if (!raw) return '-';

  const normalizedType = String(contentType || '').toLowerCase();

  if (normalizedType === 'json') {
    try {
      const parsed = JSON.parse(raw);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return raw;
    }
  }

  if (normalizedType === 'html') {
    // Keep preview safe and readable: render html as plain text.
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(raw, 'text/html');
      const text = (doc.body?.textContent || '').trim();
      return text || raw;
    } catch {
      return raw;
    }
  }

  return raw;
}

async function loadDocuments(page = filters.page) {
  if (listLoading.value) return;
  listLoading.value = true;
  listError.value = '';
  try {
    const response = await listDocuments({
      page,
      per_page: filters.per_page,
      search: filters.search.trim() || undefined
    });
    documents.value = response.documents;
    for (const doc of response.documents) {
      selectedDocumentRecordMap.value[resolveDocumentKey(doc)] = doc;
    }
    pagination.value = response.pagination;
    filters.page = response.pagination.page;
    if (documents.value.length && !selectedDocumentKey.value) {
      selectedDocumentKey.value = resolveDocumentKey(documents.value[0]);
    } else if (selectedDocumentKey.value && !documents.value.some((doc) => resolveDocumentKey(doc) === selectedDocumentKey.value)) {
      selectedDocumentKey.value = resolveDocumentKey(documents.value[0]);
    }
  } catch (error) {
    listError.value = error instanceof Error ? error.message : t('documents.message.loadFailed');
    showNotice('danger', listError.value);
  } finally {
    listLoading.value = false;
  }
}

function findDocumentByRouteTarget(target: string) {
  const normalized = String(target || '').trim().toLowerCase();
  if (!normalized) return null;
  return documents.value.find((doc) => {
    const candidates = [
      resolveDocumentKey(doc),
      doc.document_key,
      doc.file_name,
      doc.filename,
      doc.relative_path,
      doc.file_path
    ]
      .filter(Boolean)
      .map((item) => String(item).trim().toLowerCase());
    return candidates.includes(normalized);
  }) || null;
}

function resolveDocumentRowClass(row: Record<string, unknown>) {
  const key = resolveDocumentKey(row as DocumentRecord);
  return highlightDocumentKeys.value.has(key) ? 'tp-doc-row-highlight' : '';
}

function resolveRequirementItemClass(reqId: string) {
  const id = String(reqId || '').trim();
  return id && highlightRequirementIds.value.has(id) ? 'tp-requirement-highlight' : '';
}

function highlightDocumentRows(documentKeys: string[]) {
  const keys = documentKeys.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 12);
  if (!keys.length) return;
  highlightDocumentKeys.value = new Set(keys);
  if (highlightDocumentTimer.value !== null) {
    window.clearTimeout(highlightDocumentTimer.value);
  }
  highlightDocumentTimer.value = window.setTimeout(() => {
    highlightDocumentKeys.value = new Set();
    highlightDocumentTimer.value = null;
  }, 3600);
}

function highlightRequirements(reqIds: string[]) {
  const ids = reqIds.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 20);
  if (!ids.length) return;
  highlightRequirementIds.value = new Set(ids);
  if (highlightRequirementTimer.value !== null) {
    window.clearTimeout(highlightRequirementTimer.value);
  }
  highlightRequirementTimer.value = window.setTimeout(() => {
    highlightRequirementIds.value = new Set();
    highlightRequirementTimer.value = null;
  }, 4200);
}

async function scrollToFirstHighlightedDocument() {
  await nextTick();
  window.setTimeout(() => {
    const row = document.querySelector('.tp-doc-row-highlight') as HTMLElement | null;
    row?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 80);
}

async function scrollToFirstHighlightedRequirement() {
  await nextTick();
  window.setTimeout(() => {
    const node = document.querySelector('.tp-requirement-highlight') as HTMLElement | null;
    node?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 80);
}

async function handleUploadRouteAction() {
  const fromUpload = String(route.query.fromUpload || '') === '1';
  const target = String(route.query.target || '').trim();
  if (!fromUpload || !target) return;

  const targetDocument = findDocumentByRouteTarget(target);
  if (!targetDocument) {
    showNotice('warning', t('documents.message.selectDocumentFirst'));
    return;
  }

  const queryAnalysisType = String(route.query.analysisType || '').trim() as DocumentAnalysisType;
  if (['requirements', 'test_points', 'business_rules', 'comprehensive'].includes(queryAnalysisType)) {
    filters.analysisType = queryAnalysisType;
  }

  if (String(route.query.autoAnalyze || '') === '1') {
    await analyzeByDocument(targetDocument);
    await scrollToAnalysisPanel();
  } else {
    await openAnalysisForDocument(targetDocument);
  }

  await router.replace({ name: 'documents' });
}

async function handleRequirementRouteAction() {
  const fromRequirements = String(route.query.fromRequirements || '') === '1';
  const ridsRaw = String(route.query.rids || '').trim();
  if (!fromRequirements || !ridsRaw) return;

  const reqIds = ridsRaw.split(',').map((item) => item.trim()).filter(Boolean).slice(0, 20);
  if (!reqIds.length) return;

  let sourceFile = '';
  try {
    const reqResp = await getDocumentRequirements({
      page: 1,
      per_page: 50,
      search: reqIds[0]
    });
    const matched = reqResp.requirements.find((item) => reqIds.includes(String(item.req_id || '').trim()));
    sourceFile = String(matched?.source_file || '').trim();
  } catch {
    sourceFile = '';
  }

  if (sourceFile) {
    filters.search = sourceFile;
    filters.page = 1;
    await loadDocuments(1);
  }

  const normalizedSource = sourceFile.toLowerCase();
  const targetDocument = documents.value.find((doc) => {
    const candidates = [
      resolveDocumentLabel(doc),
      doc.file_name,
      doc.filename,
      doc.file_path,
      doc.relative_path
    ]
      .filter(Boolean)
      .map((item) => String(item).trim().toLowerCase());
    if (!normalizedSource) return false;
    return candidates.some((item) => item.includes(normalizedSource) || normalizedSource.includes(item));
  }) || documents.value[0] || null;

  if (targetDocument) {
    const key = resolveDocumentKey(targetDocument);
    selectedDocumentKey.value = key;
    highlightDocumentRows([key]);
    await scrollToFirstHighlightedDocument();
    await openAnalysisForDocument(targetDocument);
    highlightRequirements(reqIds);
    await scrollToFirstHighlightedRequirement();
  } else {
    highlightRequirements(reqIds);
  }

  showNotice('success', t('common.feedback.success'), t('documents.result.selected'));
  const nextQuery = { ...route.query } as Record<string, unknown>;
  delete nextQuery.fromRequirements;
  delete nextQuery.rids;
  delete nextQuery.at;
  await router.replace({ path: route.path, query: nextQuery });
}

async function handleRefresh() {
  await loadDocuments(filters.page || 1);
  if (!listError.value) {
    showNotice('success', t('documents.message.refreshSuccess'));
  }
}

async function handleSearch() {
  filters.page = 1;
  await loadDocuments(1);
}

function selectDocument(row: Record<string, unknown>) {
  const doc = row as DocumentRecord;
  selectedDocumentKey.value = resolveDocumentKey(doc);
}

function handleDocumentSelectionUpdate(values: Array<string | number>) {
  selectedDocumentKeys.value = values;
}

async function handleDocumentToggleAll(checked: boolean) {
  if (!checked) {
    selectedDocumentKeys.value = [];
    return;
  }
  const allDocs = await fetchAllFilteredDocuments();
  selectedDocumentKeys.value = allDocs.map((doc) => resolveDocumentKey(doc));
  const nextMap = { ...selectedDocumentRecordMap.value };
  for (const doc of allDocs) {
    nextMap[resolveDocumentKey(doc)] = doc;
  }
  selectedDocumentRecordMap.value = nextMap;
}

async function fetchAllFilteredDocuments() {
  const allDocs: DocumentRecord[] = [];
  let page = 1;
  const perPage = 200;
  while (true) {
    const response = await listDocuments({
      page,
      per_page: perPage,
      search: filters.search.trim() || undefined
    });
    allDocs.push(...response.documents);
    if (!response.pagination.has_next || page >= (response.pagination.pages || 1)) break;
    page += 1;
  }
  return allDocs;
}

async function analyzeDocumentRow(doc: DocumentRecord) {
  selectedDocumentKey.value = resolveDocumentKey(doc);
  await analyzeByDocument(doc);
}

async function previewDocumentRow(doc: DocumentRecord) {
  selectedDocumentKey.value = resolveDocumentKey(doc);
  await loadPreviewByDocument(doc);
}

async function reanalyzeDocumentRow(doc: DocumentRecord) {
  selectedDocumentKey.value = resolveDocumentKey(doc);
  showAnalysisPanel.value = true;
  analysisError.value = '';
  analyzeLoading.value = true;
  try {
    const result = await reanalyzeDocument(resolveReanalyzeId(doc), {
      analysis_type: filters.analysisType
    });
    currentAnalysis.value = result;
    currentAnalysisDocumentKey.value = resolveDocumentKey(doc);
    showNotice(
      'success',
      result.message || t('documents.message.analyzeSuccess'),
      8000
    );
  } catch (error) {
    analysisError.value = error instanceof Error ? error.message : t('documents.message.analyzeFailed');
    showNotice('danger', analysisError.value);
  } finally {
    analyzeLoading.value = false;
  }
}

function resolveDeleteDocumentId(doc: DocumentRecord) {
  return doc.filename || doc.relative_path || doc.file_path || String(doc.id);
}

async function deleteDocumentsByRows(rows: DocumentRecord[]) {
  if (!rows.length) {
    showNotice('warning', t('documents.message.noDocumentSelection'));
    return;
  }

  const results = await Promise.allSettled(rows.map((doc) => deleteDocument(resolveDeleteDocumentId(doc))));
  const successCount = results.filter((item) => item.status === 'fulfilled').length;
  const failedCount = rows.length - successCount;

  if (failedCount > 0) {
    showNotice('warning', t('documents.message.deleteDocumentsPartial', { success: successCount, failed: failedCount }));
  } else {
    showNotice('success', t('documents.message.deleteDocumentSuccess'));
  }

  const deletedKeys = new Set(rows.map((doc) => resolveDocumentKey(doc)));
  if (selectedDocument.value && deletedKeys.has(resolveDocumentKey(selectedDocument.value))) {
    currentAnalysis.value = null;
    currentAnalysisDocumentKey.value = '';
    selectedDocumentKey.value = '';
  }
  selectedDocumentKeys.value = [];
  await loadDocuments(1);
}

async function handleDeleteSingleDocument(doc: DocumentRecord) {
  deleteConfirmTitle.value = t('documents.actions.deleteDocuments');
  deleteConfirmMessage.value = t('documents.confirm.deleteDocuments');
  deleteConfirmButtonText.value = t('common.actions.delete');
  deleteConfirmVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteDocumentsByRows([doc]);
  };
  deleteConfirmVisible.value = true;
}

async function handleDeleteSelectedDocuments() {
  const rows = documents.value.filter((doc) => selectedDocumentKeys.value.includes(resolveDocumentKey(doc)));
  if (!rows.length) {
    showNotice('warning', t('documents.message.noDocumentSelection'));
    return;
  }
  deleteConfirmTitle.value = t('documents.actions.deleteDocuments');
  deleteConfirmMessage.value = t('documents.confirm.deleteDocuments');
  deleteConfirmButtonText.value = t('common.actions.delete');
  deleteConfirmVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteDocumentsByRows(rows);
  };
  deleteConfirmVisible.value = true;
}

async function analyzeByDocument(doc: DocumentRecord) {
  if (!doc) {
    showNotice('warning', t('documents.message.selectDocumentFirst'));
    return;
  }

  analysisError.value = '';
  showAnalysisPanel.value = true;
  analyzeLoading.value = true;
  try {
    const analysisType = filters.analysisType;
    const analyzePath = resolveAnalyzePath(doc);
    try {
      const result = await analyzeDocument({
        file_path: analyzePath,
        analysis_type: analysisType
      });
      currentAnalysis.value = result;
      currentAnalysisDocumentKey.value = resolveDocumentKey(doc);
      showNotice(
        'success',
        result.message || t('documents.message.analyzeSuccess'),
        8000
      );
      return;
    } catch {
      const fallbackResult = await reanalyzeDocument(resolveReanalyzeId(doc), {
        analysis_type: analysisType
      });
      currentAnalysis.value = fallbackResult;
      currentAnalysisDocumentKey.value = resolveDocumentKey(doc);
      showNotice(
        'success',
        fallbackResult.message || t('documents.message.analyzeSuccess'),
        8000
      );
    }
  } catch (error) {
    analysisError.value = error instanceof Error ? error.message : t('documents.message.analyzeFailed');
    showNotice('danger', analysisError.value);
  } finally {
    analyzeLoading.value = false;
  }
}

function toggleRequirementSelection(reqId: string, checked: boolean) {
  if (checked) {
    if (!selectedRequirementIds.value.includes(reqId)) {
      selectedRequirementIds.value = [...selectedRequirementIds.value, reqId];
    }
    return;
  }
  selectedRequirementIds.value = selectedRequirementIds.value.filter((item) => item !== reqId);
}

function toggleSelectAllRequirements(checked: boolean) {
  selectedRequirementIds.value = checked ? analysisRequirements.value.map((item) => item.req_id) : [];
}

async function deleteRequirementsByIds(reqIds: string[]) {
  if (!reqIds.length) {
    showNotice('warning', t('documents.message.noRequirementSelection'));
    return;
  }
  const results = await Promise.allSettled(reqIds.map((reqId) => deleteRequirement(reqId)));
  const successCount = results.filter((item) => item.status === 'fulfilled').length;
  const failedCount = reqIds.length - successCount;

  if (failedCount > 0) {
    showNotice('warning', t('documents.message.deleteRequirementsPartial', { success: successCount, failed: failedCount }));
  } else {
    showNotice('success', t('documents.message.deleteRequirementSuccess'));
  }

  if (currentAnalysis.value) {
    currentAnalysis.value = {
      ...currentAnalysis.value,
      requirements: currentAnalysis.value.requirements.filter((item) => !reqIds.includes(item.req_id)),
      saved_requirements: (currentAnalysis.value.saved_requirements || []).filter((item) => !reqIds.includes(item.req_id))
    };
  }
  selectedRequirementIds.value = selectedRequirementIds.value.filter((id) => !reqIds.includes(id));
  // 历史需求独立页会在其自身加载/刷新数据
}

async function handleDeleteSingleRequirement(reqId: string) {
  deleteConfirmTitle.value = t('documents.actions.deleteRequirements');
  deleteConfirmMessage.value = t('documents.confirm.deleteRequirements');
  deleteConfirmButtonText.value = t('common.actions.delete');
  deleteConfirmVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteRequirementsByIds([reqId]);
  };
  deleteConfirmVisible.value = true;
}

async function handleDeleteSelectedRequirements() {
  if (!selectedRequirementIds.value.length) {
    showNotice('warning', t('documents.message.noRequirementSelection'));
    return;
  }
  const reqIds = [...selectedRequirementIds.value];
  deleteConfirmTitle.value = t('documents.actions.deleteRequirements');
  deleteConfirmMessage.value = t('documents.confirm.deleteRequirements');
  deleteConfirmButtonText.value = t('common.actions.delete');
  deleteConfirmVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteRequirementsByIds(reqIds);
  };
  deleteConfirmVisible.value = true;
}

async function runDeleteConfirmAction() {
  const action = deleteConfirmAction.value;
  deleteConfirmAction.value = null;
  if (action) await action();
}

function clearDeleteConfirm() {
  deleteConfirmAction.value = null;
}

async function handleAnalyzeSelected() {
  if (!selectedDocument.value) {
    showNotice('warning', t('documents.message.selectDocumentFirst'));
    return;
  }
  await analyzeByDocument(selectedDocument.value);
}

async function loadPreviewByDocument(doc: DocumentRecord) {
  previewPanelVisible.value = true;
  previewError.value = '';
  previewLoading.value = true;
  try {
    const previewId = resolveReanalyzeId(doc);
    currentPreview.value = await getDocumentPreview(previewId);
  } catch (error) {
    currentPreview.value = null;
    previewError.value = error instanceof Error ? error.message : t('documents.message.previewFailed');
    showNotice('danger', previewError.value);
  } finally {
    previewLoading.value = false;
  }
}

function closePreviewPanel() {
  previewPanelVisible.value = false;
}

function handlePreviewCopied() {
  showNotice('success', t('documents.message.previewCopySuccess'), 1800);
}

function handlePreviewCopyFailed() {
  showNotice('warning', t('documents.message.previewCopyFailed'), 2600);
}

async function handleGenerateCases() {
  let requirementsToGenerate: DocumentRequirementRecord[] = [];
  let sourceCount = 0;
  let sourceKind: 'document' | 'requirement' = 'requirement';
  let skippedDocumentCount = 0;
  if (analysisRequirements.value.length > 0) {
    const selectedSet = new Set(selectedRequirementIds.value);
    requirementsToGenerate = selectedSet.size
      ? analysisRequirements.value.filter((item) => selectedSet.has(item.req_id))
      : analysisRequirements.value;
    sourceCount = selectedSet.size || analysisRequirements.value.length;
    sourceKind = 'requirement';
  } else {
    const selectedRows = selectedAnalyzedDocuments.value;
    skippedDocumentCount = Math.max(selectedDocuments.value.length - selectedRows.length, 0);
    if (!selectedRows.length) {
      showNotice('warning', t('documents.message.noAnalysisResult'));
      return;
    }
    const requirementGroups = await Promise.all(
      selectedRows.map(async (doc) => {
        const sourceFile = resolveDocumentLabel(doc);
        if (!sourceFile || sourceFile === t('documents.table.empty')) return [];
        try {
          const response = await getDocumentRequirements({
            page: 1,
            per_page: 200,
            source_file: sourceFile
          });
          return response.requirements;
        } catch {
          return [];
        }
      })
    );
    requirementsToGenerate = requirementGroups.flat();
    sourceCount = selectedRows.length;
    sourceKind = 'document';
  }

  if (!requirementsToGenerate.length) {
    showNotice('warning', t('documents.message.noAnalysisResult'));
    return;
  }

  if (sourceCount > 1) {
    deleteConfirmTitle.value = t('documents.confirm.batchGenerateTitle');
    deleteConfirmMessage.value = t(
      sourceKind === 'document'
        ? 'documents.confirm.batchGenerateByDocumentsMessage'
        : 'documents.confirm.batchGenerateByRequirementsMessage',
      {
        count: sourceCount,
        reqCount: requirementsToGenerate.length,
        caseCount: requirementsToGenerate.length * 3,
        skippedCount: skippedDocumentCount
      }
    );
    deleteConfirmButtonText.value = t('common.actions.confirm');
    deleteConfirmVariant.value = 'warning';
    deleteConfirmAction.value = async () => {
      await executeGenerateCases(requirementsToGenerate);
    };
    deleteConfirmVisible.value = true;
    return;
  }

  await executeGenerateCases(requirementsToGenerate);
}

async function executeGenerateCases(requirementsToGenerate: DocumentRequirementRecord[]) {
  if (!requirementsToGenerate.length) return;

  generating.value = true;
  try {
    const response = await generateCasesFromAnalysis({
      requirements: requirementsToGenerate
    });
    const count = response.total ?? response.cases?.length ?? requirementsToGenerate.length;
    showNotice('success', response.message || `${t('documents.message.generateSuccess')} (${count})`);
    await router.push('/cases');
  } catch (error) {
    showNotice('danger', error instanceof Error ? error.message : t('documents.message.generateFailed'));
  } finally {
    generating.value = false;
  }
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'requirements.xlsx';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function handleExportRequirements() {
  if (!analysisRequirements.value.length || exportingRequirements.value) return;
  const selectedSet = new Set(selectedRequirementIds.value);
  const reqIds = selectedSet.size
    ? analysisRequirements.value.filter((item) => selectedSet.has(item.req_id)).map((item) => item.req_id)
    : analysisRequirements.value.map((item) => item.req_id);
  if (!reqIds.length) {
    showNotice('warning', t('documents.message.noRequirementSelection'));
    return;
  }

  try {
    exportingRequirements.value = true;
    const result = await exportRequirementsExcel({ req_ids: reqIds });
    triggerDownload(result.blob, result.filename);
    showNotice('success', t('documents.message.exportRequirementsSuccess'));
  } catch (error) {
    showNotice('danger', error instanceof Error ? error.message : t('documents.message.exportRequirementsFailed'));
  } finally {
    exportingRequirements.value = false;
  }
}

onMounted(async () => {
  await loadDocuments(1);
  await handleUploadRouteAction();
  await handleRequirementRouteAction();
});

watch(
  () => [route.query.fromRequirements, route.query.rids, route.query.at],
  async () => {
    await handleRequirementRouteAction();
  }
);

onBeforeUnmount(() => {
  if (highlightDocumentTimer.value !== null) {
    window.clearTimeout(highlightDocumentTimer.value);
    highlightDocumentTimer.value = null;
  }
  if (highlightRequirementTimer.value !== null) {
    window.clearTimeout(highlightRequirementTimer.value);
    highlightRequirementTimer.value = null;
  }
});
</script>

<style scoped>
.tp-doc-page-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.tp-analysis-requirement-item {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  padding: 10px 12px !important;
  background: color-mix(in srgb, var(--tp-bg-surface) 94%, var(--tp-color-primary-600) 6%);
}

:deep(.tp-doc-row-highlight) {
  background: color-mix(in srgb, var(--tp-color-primary-500) 14%, transparent);
  animation: tp-doc-highlight-fade 3.6s ease forwards;
}

.tp-requirement-highlight {
  outline: 2px solid color-mix(in srgb, var(--tp-color-primary-600) 50%, transparent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--tp-color-primary-600) 12%, transparent);
  transition: outline-color 0.25s ease, box-shadow 0.25s ease;
}

@keyframes tp-doc-highlight-fade {
  0% { background: color-mix(in srgb, var(--tp-color-primary-500) 22%, transparent); }
  100% { background: transparent; }
}
</style>
