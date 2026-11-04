<template>
  <section :class="pageRootMarkedClass(pageMarkerDocuments)">
    <PageNoticeBanner
      :notice="pageBanner"
      @close="clearPageBanner"
      @action="runPageBannerAction"
    />

    <div :class="grid12Class">
      <div :class="colSpan12">
        <PagePanel
          class="mb-4"
          :title="t('documents.tabs.manage')"
          :subtitle="t('documents.toolbar.manageLead')"
        >
          <template #actions>
            <div :class="pageToolbarStripClass">
              <TpButton variant="ghost" size="sm" :loading="listRefreshLoading" @click="handleRefresh">
                {{ t('common.actions.refresh') }}
              </TpButton>
              <span v-if="caseRagStatusLabel" class="whitespace-nowrap text-xs text-muted-foreground">{{ caseRagStatusLabel }}</span>
              <TpButton
                variant="primary"
                size="sm"
                :loading="generating"
                :disabled="generating || !canGenerateCases"
                @click="handleGenerateCases"
              >
                {{ generating ? t('documents.actions.generating') : t('documents.actions.generateCases') }}
              </TpButton>
              <ToolbarOverflowMenu>
                <DropdownMenuItem
                  v-if="!showAnalysisPanel && currentAnalysis"
                  @select="showAnalysisPanel = true"
                >
                  {{ t('documents.analysis.showPanel') }}
                </DropdownMenuItem>
                <DropdownMenuItem
                  :disabled="exportingRequirements || !analysisRequirements.length"
                  @select="handleExportRequirements"
                >
                  {{
                    exportingRequirements
                      ? t('documents.actions.exportingRequirements')
                      : t('documents.actions.exportRequirements')
                  }}
                </DropdownMenuItem>
              </ToolbarOverflowMenu>
            </div>
          </template>

          <ToolbarBulkBar :count="selectedDocumentKeys.length" @clear="clearDocumentSelection">
            <TpButton
              variant="ghost"
              size="sm"
              :disabled="analyzeLoading || !selectedDocument"
              @click="handleAnalyzeSelected"
            >
              {{ t('documents.actions.analyzeCurrent') }}
            </TpButton>
            <TpButton
              variant="danger"
              size="sm"
              :disabled="analyzeLoading || !selectedDocumentKeys.length"
              @click="handleDeleteSelectedDocuments"
            >
              {{ t('documents.actions.deleteDocuments') }}
            </TpButton>
          </ToolbarBulkBar>

          <TableToolbar
            :title="t('documents.filters.title')"
            :subtitle="filterToolbarSubtitle"
          >
            <template #filters>
              <TableFilterForm @submit="handleSearch">
                <TableFilterInput
                  v-model="filters.search"
                  :placeholder="t('documents.filters.keywordPlaceholder')"
                  :aria-label="t('documents.filters.keywordLabel')"
                />
                <TableFilterSelect
                  v-model="filters.analysisType"
                  class="min-w-[160px]"
                  :aria-label="t('documents.filters.analysisTypeLabel')"
                >
                  <option v-for="option in analysisTypeOptions" :key="`filter-${option.value}`" :value="option.value">
                    {{ option.label }}
                  </option>
                </TableFilterSelect>
                <TpButton :loading="listLoading" type="submit">
                  {{ t('documents.filters.apply') }}
                </TpButton>
              </TableFilterForm>
            </template>
          </TableToolbar>

          <div :class="pageSectionDivideClass">
          <div v-if="listError" class="mb-4">
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
            keep-content-while-loading
            :loading-title="t('documents.table.loading')"
            :empty-title="t('documents.table.empty')"
            :empty-message="''"
            :selectable="true"
            :selected-keys="selectedDocumentKeys"
            row-key="document_key"
            @update:selectedKeys="handleDocumentSelectionUpdate"
            :managed-select-all="true"
            @toggleAll="handleDocumentToggleAll"
            @rowClick="selectDocument"
          >
            <template #toolbar>
              <TableToolbar :title="t('documents.table.title')" :pagination="pagination" />
            </template>
            <template #cell-name="{ row }">
              <div :class="dataTitleClass">{{ resolveDocumentLabel(row as DocumentRecord) }}</div>
              <TpTruncateText
                v-if="(row as DocumentRecord).description"
                :text="(row as DocumentRecord).description || ''"
                :class="[dataSubtitleDenseClass, 'max-w-96']"
              />
            </template>
            <template #cell-type="{ row }">
              {{ resolveFileTypeLabel((row as DocumentRecord).file_type) }}
            </template>
            <template #cell-status="{ row }">
              <TpTag :variant="documentStatusTagVariant((row as DocumentRecord).status || (row as DocumentRecord).analysis_status)">
                {{ resolveStatusLabel((row as DocumentRecord).status || (row as DocumentRecord).analysis_status) }}
              </TpTag>
            </template>
            <template #cell-updatedAt="{ row }">
              {{ formatDocDateTime((row as DocumentRecord).updated_time || (row as DocumentRecord).created_time) }}
            </template>
            <template #cell-actions="{ row }">
              <div class="flex justify-end gap-2">
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
            <template #footer>
              <ListTablePager :pagination="pagination" @change="changePage" />
            </template>
          </BaseTable>
          </div>
        </PagePanel>

        <div
          v-if="showAnalysisPanel || analyzeLoading || analysisError || currentAnalysis"
          ref="analysisPanelRef"
        >
          <PagePanel>
            <template #header>
              <div>
                <div :class="panelTitleClass">{{ t('documents.analysis.title') }}</div>
                <div :class="panelSubtitleClass">
                  {{ selectedDocument ? `${t('documents.analysis.sourceDocument')}: ${resolveDocumentLabel(selectedDocument)}` : t('documents.analysis.empty') }}
                </div>
              </div>
            </template>
            <template #actions>
              <TpButton size="sm" variant="ghost" @click="showAnalysisPanel = false">
                {{ t('documents.analysis.hidePanel') }}
              </TpButton>
              <TpButton size="sm" :loading="generating" :disabled="generating || !analysisRequirements.length" @click="handleGenerateCases">
                {{ t('documents.actions.generateCases') }}
              </TpButton>
            </template>

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
                <div class="mt-1.5 text-sm text-muted-foreground">{{ analysisSummaryText }}</div>
              </template>

              <template #metrics>
                <div :class="grid12Class">
                  <div v-for="card in summaryCards" :key="card.key" :class="colSpan12Md6Min1400_3">
                    <div :class="nestedMetricBlockClass">
                      <div :class="kpiLabelClass">{{ card.label }}</div>
                      <div :class="kpiValueClass">{{ card.value }}</div>
                      <div v-if="card.hint" :class="kpiHintClass">{{ card.hint }}</div>
                    </div>
                  </div>
                </div>
              </template>

              <template #evidence>
                <div v-if="analysisRequirements.length" class="grid gap-2">
                  <div :class="sectionTitleClass">{{ t('documents.analysis.requirementsTitle') }}</div>
                  <div v-if="selectedDocument" :class="captionTextClass">
                    {{ t('documents.analysis.currentDocument') }}: {{ resolveDocumentLabel(selectedDocument) }}
                  </div>
                  <div class="flex items-center justify-between">
                    <label :class="inlineToggleLabelClass">
                      <input
                        :class="tableCheckboxClass"
                        type="checkbox"
                        :checked="allRequirementsSelected"
                        @change="toggleSelectAllRequirements(($event.target as HTMLInputElement).checked)"
                      />
                      <span :class="captionTextClass">{{ t('documents.actions.selectAllRequirements') }}</span>
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
                    :class="[documentsAnalysisRequirementItemClass, resolveRequirementItemClass(item.req_id)]"
                    :data-req-id="item.req_id"
                  >
                    <div class="flex items-start justify-between gap-2">
                      <label :class="inlineToggleLabelClass">
                        <input
                          :class="tableCheckboxClass"
                          type="checkbox"
                          :checked="selectedRequirementIds.includes(item.req_id)"
                          @change="toggleRequirementSelection(item.req_id, ($event.target as HTMLInputElement).checked)"
                        />
                        <span :class="captionTextClass">{{ item.req_id }}</span>
                      </label>
                      <div class="flex shrink-0 gap-2">
                        <TpButton variant="primary" size="sm" @click="openRequirementEditor(item)">
                          {{ t('common.actions.edit') }}
                        </TpButton>
                        <TpButton variant="danger" size="sm" @click="handleDeleteSingleRequirement(item.req_id)">
                          {{ t('common.actions.delete') }}
                        </TpButton>
                      </div>
                    </div>
                    <div :class="[dataTitleClass, 'mt-2']">{{ item.title }}</div>
                    <div :class="dataSubtitleClass">{{ item.content }}</div>
                  </div>
                  <ListTablePager
                    class="mt-2"
                    :pagination="analysisRequirementPagination"
                    :show-summary="true"
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
                <pre :class="documentsRawBlockClass">{{ analysisRawText }}</pre>
              </template>
            </AiResultCard>
          </template>
          </PagePanel>
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
    <RequirementEditDrawer
      :visible="requirementEditVisible"
      :record="editingRequirement"
      :type-options="analysisRequirementTypeOptions"
      :priority-options="analysisRequirementPriorityOptions"
      @close="closeRequirementEditor"
      @saved="handleRequirementSaved"
      @error="(message) => showNotice('danger', message, { title: t('common.status.error') })"
    />

    <ConfirmDialog
      v-model="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-text="confirmDialog.confirmText"
      :cancel-text="confirmDialog.cancelText"
      :confirm-variant="confirmDialog.variant"
      @confirm="confirmDialog.handleConfirm"
      @cancel="confirmDialog.handleCancel"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import { TableFilterForm, TableFilterInput, TableFilterSelect } from '@/components/common/table';
import {
  colSpan12,
  colSpan12Md6Min1400_3,
  grid12Class,
  pageMarkerDocuments,
  pageRootMarkedClass,
  pageSectionDivideClass
} from '@/lib/page-layout-ui';
import ToolbarBulkBar from '@/components/common/ToolbarBulkBar.vue';
import ToolbarOverflowMenu from '@/components/common/ToolbarOverflowMenu.vue';
import { DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { type ListFetchMode } from '@/lib/list-fetch-mode';
import { documentStatusTagVariant } from '@/lib/enum-tag-ui';
import { useListPageChange } from '@/composables/useListPageChange';
import { usePaginatedList } from '@/composables/usePaginatedList';
import { useTimedHighlight } from '@/composables/useTimedHighlight';
import { pageToolbarStripClass } from '@/lib/page-chrome-ui';
import { captionTextClass } from '@/lib/page-typography';
import { panelSubtitleClass, panelTitleClass } from '@/lib/panel-ui';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import {
  dataSubtitleClass,
  dataSubtitleDenseClass,
  dataTitleClass,
  inlineToggleLabelClass,
  kpiHintClass,
  kpiLabelClass,
  kpiValueClass,
  nestedMetricBlockClass,
  sectionTitleClass
} from '@/lib/page-typography';
import {
  documentsAnalysisRequirementItemClass,
  documentsRawBlockClass,
  documentsRequirementHighlightActiveClass,
  documentsRequirementHighlightClass,
  documentsRowHighlightActiveClass,
  documentsRowHighlightClass
} from '@/lib/documents-ui';
import { buildRequirementTypeSelectOptions } from '@/lib/requirement-type-ui';
import { tableCheckboxClass } from '@/lib/table-ui';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import RequirementEditDrawer from '@/components/documents/RequirementEditDrawer.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import ListTablePager from '@/components/common/ListTablePager.vue';
import { useConfirmAction } from '@/composables/useConfirmAction';
import { formatBytes, formatDateTime } from '@/lib/format';
import { triggerBlobDownload } from '@/lib/download';
import PreviewDrawer from '@/components/common/PreviewDrawer.vue';
import AiResultCard from '@/components/ui/AiResultCard.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpTruncateText from '@/components/ui/base/TpTruncateText.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAiResult } from '@/composables/useAiResult';
import { useCaseGenerationRagStatus } from '@/composables/useCaseGenerationRagStatus';
import { usePageNotifier, type PageNoticeExtras } from '@/composables/usePageNotifier';
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

interface SelectOption {
  value: DocumentAnalysisType;
  label: string;
}

const { t, locale } = useI18n();
const route = useRoute();
const router = useRouter();
const { label: caseRagStatusLabel, refresh: refreshCaseRagStatus } = useCaseGenerationRagStatus();
const documents = ref<DocumentRecord[]>([]);
const currentAnalysis = ref<DocumentAnalysisResult | null>(null);
const selectedDocumentKey = ref<string>('');
const listRefreshLoading = ref(false);
const analyzeLoading = ref(false);
const generating = ref(false);
const exportingRequirements = ref(false);
const documentRowHighlight = useTimedHighlight(4200);
const requirementRowHighlight = useTimedHighlight(4200);
const analysisError = ref('');
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  runBannerAction: runPageBannerAction,
  showNotice: notifyShowNotice
} = usePageNotifier();
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
const confirmDialog = useConfirmAction(t('common.actions.cancel'));
const requirementEditVisible = ref(false);
const editingRequirement = ref<DocumentRequirementRecord | null>(null);

const analysisRequirementTypeOptions = computed(() => buildRequirementTypeSelectOptions(t));

const analysisRequirementPriorityOptions = computed(() => [
  { value: 'P0', label: 'P0' },
  { value: 'P1', label: 'P1' },
  { value: 'P2', label: 'P2' },
  { value: 'P3', label: 'P3' }
]);

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

const { listLoading, listError, loadPage: loadDocumentsPage } = usePaginatedList(documents, {
  refreshLoading: listRefreshLoading,
  pagination
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

function documentListQuery(page: number, perPage: number) {
  return {
    page,
    per_page: perPage,
    search: filters.search.trim() || undefined,
    analysis_type:
      filters.analysisType === 'comprehensive' ? undefined : filters.analysisType
  };
}

function requirementApiTypeForFilter(analysisType: DocumentAnalysisType): string | undefined {
  if (analysisType === 'comprehensive' || analysisType === 'requirements') return undefined;
  if (analysisType === 'test_points') return 'functional';
  if (analysisType === 'business_rules') return 'business';
  return undefined;
}

function splitRequirementsByKind(requirements: DocumentRequirementRecord[]) {
  const testPoints = requirements.filter((item) => {
    const type = String(item.type || '').toLowerCase();
    return type === 'functional' || type === 'test_point' || item.is_test_point;
  });
  const businessRules = requirements.filter((item) => {
    const type = String(item.type || '').toLowerCase();
    return type === 'business' || type === 'business_rule' || item.is_business_rule;
  });
  const coreRequirements = requirements.filter((item) => {
    const type = String(item.type || '').toLowerCase();
    return type !== 'business' && type !== 'business_rule' && !item.is_business_rule;
  });
  return { testPoints, businessRules, coreRequirements };
}

function resolveVisibleRequirements(
  requirements: DocumentRequirementRecord[],
  analysisType: DocumentAnalysisType
) {
  const { testPoints, businessRules, coreRequirements } = splitRequirementsByKind(requirements);
  if (analysisType === 'comprehensive') return requirements;
  if (analysisType === 'test_points') return testPoints;
  if (analysisType === 'business_rules') return businessRules;
  return coreRequirements;
}

function buildAnalysisSnapshot(
  requirements: DocumentRequirementRecord[],
  analysisType: DocumentAnalysisType,
  message?: string
): DocumentAnalysisResult {
  const { testPoints, businessRules, coreRequirements } = splitRequirementsByKind(requirements);
  const visible = resolveVisibleRequirements(requirements, analysisType);
  return {
    success: true,
    message: message || t('documents.message.resultLoadedFromHistory'),
    analysis_type: analysisType,
    requirements: visible,
    test_points: testPoints,
    business_rules: businessRules,
    saved_requirements: [...requirements],
    summary: {
      requirements_count: coreRequirements.length,
      test_points_count: testPoints.length,
      business_rules_count: businessRules.length,
      total_count: visible.length
    }
  };
}

const analysisRequirements = computed<DocumentRequirementRecord[]>(() => {
  const stored = currentAnalysis.value?.saved_requirements?.length
    ? currentAnalysis.value.saved_requirements
    : currentAnalysis.value?.requirements || [];
  return resolveVisibleRequirements(stored, filters.analysisType);
});
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
  const base = t('documents.result.title');
  return selectedDocument.value
    ? `${base} · ${t('documents.analysis.title')} - ${resolveDocumentLabel(selectedDocument.value)}`
    : `${base} · ${t('documents.analysis.title')}`;
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

const filterToolbarSubtitle = computed(() => {
  const parts: string[] = [];
  if (selectedDocument.value) {
    parts.push(`${t('documents.result.selected')}: ${resolveDocumentLabel(selectedDocument.value)}`);
  } else {
    parts.push(t('documents.message.selectDocumentFirst'));
  }
  if (selectedDocumentKeys.value.length) {
    parts.push(t('documents.result.selectedDocumentsCount', { count: selectedDocumentKeys.value.length }));
  }
  return parts.join(' · ');
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
    size: formatBytes(currentPreview.value.file_size, { zero: '-' })
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

watch(analysisRequirements, () => {
  analysisRequirementPage.value = 1;
  selectedRequirementIds.value = selectedRequirementIds.value.filter((reqId) =>
    analysisRequirements.value.some((item) => item.req_id === reqId)
  );
});

function showNotice(
  type: 'success' | 'danger' | 'warning' | 'info',
  message: string,
  extras?: PageNoticeExtras
) {
  notifyShowNotice(type, message, extras);
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
        per_page: 500,
        source_file: doc.filename || resolveDocumentLabel(doc),
        search: filters.search.trim() || undefined,
        type: requirementApiTypeForFilter(filters.analysisType)
      });
      if (response.requirements.length > 0) {
        currentAnalysis.value = buildAnalysisSnapshot(response.requirements, filters.analysisType);
        currentAnalysisDocumentKey.value = nextKey;
      } else {
        showNotice('info', t('documents.message.resultNotReady'));
      }
    } catch (error) {
      analysisError.value = getUserFacingErrorMessage(error, t('documents.message.loadAnalysisFailed'));
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
  return doc.display_name || doc.original_filename || doc.file_name || doc.filename || t('documents.table.empty');
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

function resolvePriorityLabel(priority?: string) {
  const value = String(priority || '').trim().toLowerCase();
  if (value === 'p0' || value === 'critical') return 'P0';
  if (value === 'high' || value === 'p1') return 'P1';
  if (value === 'medium' || value === 'normal' || value === 'p2' || !value) return 'P2';
  if (value === 'low' || value === 'p3') return 'P3';
  return String(priority || '-').toUpperCase();
}

function formatDocDateTime(value?: string | null) {
  return formatDateTime(value, locale.value);
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

async function syncAnalysisWithFilters(options?: { silent?: boolean }) {
  const doc = selectedDocument.value;
  if (!doc || (!showAnalysisPanel.value && !currentAnalysis.value)) return;

  const silent = options?.silent ?? true;
  if (!silent) analyzeLoading.value = true;
  analysisError.value = '';
  try {
    const response = await getDocumentRequirements({
      page: 1,
      per_page: 500,
      source_file: doc.filename || resolveDocumentLabel(doc),
      search: filters.search.trim() || undefined,
      type: requirementApiTypeForFilter(filters.analysisType)
    });
    const key = resolveDocumentKey(doc);
    currentAnalysis.value = buildAnalysisSnapshot(
      response.requirements,
      filters.analysisType,
      response.requirements.length ? t('documents.message.resultLoadedFromHistory') : t('documents.analysis.noRequirements')
    );
    currentAnalysisDocumentKey.value = key;
    selectedRequirementIds.value = [];
    analysisRequirementPage.value = 1;
  } catch (error) {
    analysisError.value = getUserFacingErrorMessage(error, t('documents.message.loadAnalysisFailed'));
    if (!silent) showNotice('danger', analysisError.value);
  } finally {
    if (!silent) analyzeLoading.value = false;
  }
}

async function loadDocuments(page = filters.page, mode: ListFetchMode = 'page') {
  const result = await loadDocumentsPage(
    page,
    mode,
    () =>
      listDocuments(documentListQuery(page, filters.per_page)).then((response) => ({
        rows: response.documents,
        pagination: response.pagination
      })),
    {
      resolveMessage: (error) =>
        getUserFacingErrorMessage(
          error,
          filters.search.trim() ? t('documents.message.searchFailed') : t('documents.message.loadFailed')
        )
    }
  );
  if (!result) {
    const message = listError.value;
    if (message) showNotice('danger', message);
    return;
  }
  for (const doc of result.rows) {
    selectedDocumentRecordMap.value[resolveDocumentKey(doc)] = doc;
  }
  filters.page = result.pagination.page ?? page;
  if (documents.value.length && !selectedDocumentKey.value) {
    selectedDocumentKey.value = resolveDocumentKey(documents.value[0]);
  } else if (selectedDocumentKey.value && !documents.value.some((doc) => resolveDocumentKey(doc) === selectedDocumentKey.value)) {
    selectedDocumentKey.value = resolveDocumentKey(documents.value[0]);
  }
}

const { changePage } = useListPageChange(
  pagination,
  (page, mode) => loadDocuments(page, mode),
  { onAcceptPage: (page) => { filters.page = page; } }
);

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

function resolveDocumentRowClass(row: DocumentRecord) {
  const key = resolveDocumentKey(row);
  return documentRowHighlight.has(key) ? documentsRowHighlightActiveClass : '';
}

function resolveRequirementItemClass(reqId: string) {
  const id = String(reqId || '').trim();
  return id && requirementRowHighlight.has(id) ? documentsRequirementHighlightActiveClass : '';
}

function highlightDocumentRows(documentKeys: string[]) {
  documentRowHighlight.highlight(documentKeys, 3600);
}

function highlightRequirements(reqIds: string[]) {
  requirementRowHighlight.highlight(reqIds, 4200, 20);
}

async function scrollToFirstHighlightedDocument() {
  await nextTick();
  window.setTimeout(() => {
    const row = document.querySelector(`.${documentsRowHighlightClass}`) as HTMLElement | null;
    row?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 80);
}

async function scrollToFirstHighlightedRequirement() {
  await nextTick();
  window.setTimeout(() => {
    const node = document.querySelector(`.${documentsRequirementHighlightClass}`) as HTMLElement | null;
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
    await loadDocuments(1, 'filter');
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

  showNotice('success', t('documents.result.selected'), { title: t('common.feedback.success') });
  const nextQuery: LocationQueryRaw = { ...route.query };
  delete nextQuery.fromRequirements;
  delete nextQuery.rids;
  delete nextQuery.at;
  await router.replace({ path: route.path, query: nextQuery });
}

async function handleRefresh() {
  await loadDocuments(filters.page || 1, 'refresh');
  if (!listError.value) {
    showNotice('success', t('documents.message.refreshSuccess'));
  }
}

async function handleSearch() {
  filters.search = filters.search.trim();
  filters.page = 1;
  const mode: ListFetchMode = documents.value.length > 0 ? 'page' : 'filter';
  await loadDocuments(1, mode);
  await syncAnalysisWithFilters({ silent: true });
}

function selectDocument(row: DocumentRecord) {
  const doc = row;
  selectedDocumentKey.value = resolveDocumentKey(doc);
}

function handleDocumentSelectionUpdate(values: Array<string | number>) {
  selectedDocumentKeys.value = values;
}

function clearDocumentSelection() {
  selectedDocumentKeys.value = [];
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
    const response = await listDocuments(documentListQuery(page, perPage));
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
    showNotice('success', result.message || t('documents.message.analyzeSuccess'), { timeout: 8000 });
  } catch (error) {
    analysisError.value = getUserFacingErrorMessage(error, t('documents.message.analyzeFailed'));
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
  await loadDocuments(1, 'refresh');
}

async function handleDeleteSingleDocument(doc: DocumentRecord) {
  confirmDialog.open({
    title: t('documents.actions.deleteDocuments'),
    message: t('documents.confirm.deleteDocuments'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteDocumentsByRows([doc]);
    }
  });
}

async function handleDeleteSelectedDocuments() {
  const rows = documents.value.filter((doc) => selectedDocumentKeys.value.includes(resolveDocumentKey(doc)));
  if (!rows.length) {
    showNotice('warning', t('documents.message.noDocumentSelection'));
    return;
  }
  confirmDialog.open({
    title: t('documents.actions.deleteDocuments'),
    message: t('documents.confirm.deleteDocuments'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteDocumentsByRows(rows);
    }
  });
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
      showNotice('success', result.message || t('documents.message.analyzeSuccess'), { timeout: 8000 });
      return;
    } catch {
      const fallbackResult = await reanalyzeDocument(resolveReanalyzeId(doc), {
        analysis_type: analysisType
      });
      currentAnalysis.value = fallbackResult;
      currentAnalysisDocumentKey.value = resolveDocumentKey(doc);
      showNotice('success', fallbackResult.message || t('documents.message.analyzeSuccess'), { timeout: 8000 });
    }
  } catch (error) {
    analysisError.value = getUserFacingErrorMessage(error, t('documents.message.analyzeFailed'));
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

function openRequirementEditor(row: DocumentRequirementRecord) {
  editingRequirement.value = row;
  requirementEditVisible.value = true;
}

function closeRequirementEditor() {
  requirementEditVisible.value = false;
  editingRequirement.value = null;
}

function replaceRequirementInAnalysis(updated: DocumentRequirementRecord) {
  if (!currentAnalysis.value) return;
  const patch = (list: DocumentRequirementRecord[]) =>
    list.map((item) => (item.req_id === updated.req_id ? { ...item, ...updated } : item));
  currentAnalysis.value = {
    ...currentAnalysis.value,
    requirements: patch(currentAnalysis.value.requirements || []),
    saved_requirements: patch(currentAnalysis.value.saved_requirements || []),
    test_points: patch(currentAnalysis.value.test_points || []),
    business_rules: patch(currentAnalysis.value.business_rules || [])
  };
}

function handleRequirementSaved(updated: DocumentRequirementRecord) {
  closeRequirementEditor();
  replaceRequirementInAnalysis(updated);
  requirementRowHighlight.highlight([String(updated.req_id)], 4200, 20);
  showNotice('success', t('documents.requirement.updateSuccess'), { title: t('common.feedback.success') });
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
  confirmDialog.open({
    title: t('documents.actions.deleteRequirements'),
    message: t('documents.confirm.deleteRequirements'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteRequirementsByIds([reqId]);
    }
  });
}

async function handleDeleteSelectedRequirements() {
  if (!selectedRequirementIds.value.length) {
    showNotice('warning', t('documents.message.noRequirementSelection'));
    return;
  }
  const reqIds = [...selectedRequirementIds.value];
  confirmDialog.open({
    title: t('documents.actions.deleteRequirements'),
    message: t('documents.confirm.deleteRequirements'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteRequirementsByIds(reqIds);
    }
  });
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
    previewError.value = getUserFacingErrorMessage(error, t('documents.message.previewFailed'));
    showNotice('danger', previewError.value);
  } finally {
    previewLoading.value = false;
  }
}

function closePreviewPanel() {
  previewPanelVisible.value = false;
}

function handlePreviewCopied() {
  showNotice('success', t('documents.message.previewCopySuccess'), { timeout: 1800 });
}

function handlePreviewCopyFailed() {
  showNotice('warning', t('documents.message.previewCopyFailed'), { timeout: 2600 });
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
    confirmDialog.open({
      title: t('documents.confirm.batchGenerateTitle'),
      message: t(
        sourceKind === 'document'
          ? 'documents.confirm.batchGenerateByDocumentsMessage'
          : 'documents.confirm.batchGenerateByRequirementsMessage',
        {
          count: sourceCount,
          reqCount: requirementsToGenerate.length,
          caseCount: requirementsToGenerate.length * 3,
          skippedCount: skippedDocumentCount
        }
      ),
      confirmText: t('common.actions.confirm'),
      variant: 'warning',
      onConfirm: async () => {
        await executeGenerateCases(requirementsToGenerate);
      }
    });
    return;
  }

  confirmDialog.open({
    title: t('documents.actions.generateCases'),
    message: t('documents.confirm.generateCases'),
    confirmText: t('common.actions.confirm'),
    variant: 'primary',
    onConfirm: async () => {
      await executeGenerateCases(requirementsToGenerate);
    }
  });
}

async function executeGenerateCases(requirementsToGenerate: DocumentRequirementRecord[]) {
  if (!requirementsToGenerate.length) return;

  generating.value = true;
  try {
    const response = await generateCasesFromAnalysis({
      requirements: requirementsToGenerate
    });
    const count = response.total ?? response.cases?.length ?? requirementsToGenerate.length;
    const failedCount = Number(response.failed_count || 0);
    if (failedCount > 0) {
      showNotice('warning', response.message || t('documents.message.generateFailed'));
    } else {
      showNotice('success', response.message || `${t('documents.message.generateSuccess')} (${count})`);
    }
    await router.push({ name: 'cases-manage' });
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('documents.message.generateFailed')));
  } finally {
    generating.value = false;
  }
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
    triggerBlobDownload(result.blob, result.filename);
    showNotice('success', t('documents.message.exportRequirementsSuccess'));
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('documents.message.exportRequirementsFailed')));
  } finally {
    exportingRequirements.value = false;
  }
}

onMounted(async () => {
  void refreshCaseRagStatus();
  await loadDocuments(1, 'initial');
  await handleUploadRouteAction();
  await handleRequirementRouteAction();
});

watch(
  () => [route.query.fromRequirements, route.query.rids, route.query.at],
  async () => {
    await handleRequirementRouteAction();
  }
);
</script>

