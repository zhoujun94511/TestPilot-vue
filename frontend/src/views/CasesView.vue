<template>
  <section :class="pageRootMarkedClass(pageMarkerCases)">
    <PageNoticeBanner
      :notice="pageBanner"
      @close="clearPageBanner"
    />

    <PagePanel
      v-if="isGenerateMode && (generateLoading || batchLoading)"
      class="mb-4"
      :title="batchLoading ? t('cases.state.batchGeneratingTitle') : t('cases.state.generatingTitle')"
    >
      <BaseState
        variant="loading"
        :title="batchLoading ? t('cases.actions.batchGenerating') : t('cases.actions.generating')"
        :message="batchLoading ? t('cases.state.batchGeneratingHint') : t('cases.state.generatingHint')"
      />
    </PagePanel>

    <PagePanel v-if="isGenerateMode && generateKind === 'single'" class="mb-4">
      <form novalidate @submit.prevent="openGenerateConfirm">
        <TpInput
          v-model="singleForm.requirementText"
          as="textarea"
          class="mb-4"
          :label="t('cases.form.requirementLabel')"
          :helper="t('cases.form.requirementHelper')"
          helper-placement="label"
          :rows="8"
          :placeholder="t('cases.form.requirementPlaceholder')"
          required
          :error="singleRequirementError"
        />
        <div :class="[grid12Class, 'mb-4']">
          <div :class="colSpan12Md6">
            <TpInput
              v-model="singleForm.caseCount"
              as="select"
              :label="t('cases.form.caseCountLabel')"
              :options="caseCountOptions"
            />
          </div>
        </div>
        <div :class="formActionsClass">
          <TpButton variant="ghost" type="button" @click="clearSingleRequirementInput">
            {{ t('cases.actions.clearInput') }}
          </TpButton>
          <TpButton type="submit" :loading="generateLoading" :disabled="generateLoading || !singleForm.requirementText.trim()">
            {{ generateLoading ? t('cases.actions.generating') : t('cases.actions.generate') }}
          </TpButton>
        </div>
      </form>
    </PagePanel>

    <PagePanel v-if="isGenerateMode && generateKind === 'batch'" class="mb-4">
      <form novalidate @submit.prevent="openBatchConfirm">
        <TpInput
          v-model="batchForm.requirementsText"
          as="textarea"
          class="mb-4"
          :label="t('cases.form.requirementLabel')"
          :helper="t('cases.batch.requirementsHelper')"
          helper-placement="label"
          :rows="8"
          :placeholder="t('cases.batch.requirementsPlaceholder')"
          required
          :error="batchRequirementsError"
        />
        <div :class="[grid12Class, 'mb-4']">
          <div :class="colSpan12Md6">
            <TpInput
              v-model="batchForm.caseCountPerRequirement"
              as="select"
              :label="t('cases.form.caseCountLabel')"
              :options="caseCountOptions"
            />
          </div>
          <div :class="colSpan12Md6">
            <TpInput
              v-model="batchForm.processMode"
              as="select"
              :label="t('cases.batch.processModeLabel')"
              :helper="t('cases.batch.processModeHelper')"
              :options="processModeOptions"
            />
          </div>
        </div>
        <div :class="formActionsClass">
          <TpButton variant="ghost" type="button" @click="resetBatchForm">
            {{ t('cases.actions.clearInput') }}
          </TpButton>
          <TpButton type="submit" :loading="batchLoading" :disabled="batchLoading || !batchForm.requirementsText.trim()">
            {{ batchLoading ? t('cases.actions.batchGenerating') : t('cases.actions.batchGenerate') }}
          </TpButton>
        </div>
      </form>
    </PagePanel>

    <PagePanel
      v-if="isManageMode"
      :class="manageSyncedHighlight && casesSyncHighlightClass"
      :title="t('cases.tabs.manage')"
      :subtitle="t('cases.toolbar.manageLead')"
    >
      <template #actions>
        <div :class="pageToolbarStripClass">
          <TpButton variant="ghost" size="sm" :loading="listRefreshLoading" @click="handleRefresh">
            {{ t('common.actions.refresh') }}
          </TpButton>
          <TpButton variant="primary" size="sm" :loading="exporting" :disabled="exporting" @click="handleExport">
            {{ exporting ? t('cases.actions.exporting') : t('cases.actions.export') }}
          </TpButton>
          <ToolbarOverflowMenu>
            <DropdownMenuLabel>{{ t('cases.actions.export') }}</DropdownMenuLabel>
            <DropdownMenuRadioGroup v-model="exportFormat">
              <DropdownMenuRadioItem value="excel">
                {{ t('cases.actions.exportExcel') }}
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="csv">
                {{ t('cases.actions.exportCsv') }}
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="json">
                {{ t('cases.actions.exportJson') }}
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem :disabled="templateDownloading" @select="handleDownloadTemplate">
              {{
                templateDownloading
                  ? t('cases.actions.templateDownloading')
                  : t('cases.actions.downloadTemplate')
              }}
            </DropdownMenuItem>
          </ToolbarOverflowMenu>
        </div>
      </template>

      <div :class="statsSummaryPanelClass">
        <div :class="sectionTitleClass">{{ t('cases.stats.title') }}</div>
        <div :class="[grid12Class, 'mt-3']">
          <div v-for="card in statsCards" :key="card.key" :class="colSpan12Md6Min1400_3">
            <KnowledgeStatsCard
              :label="card.label"
              :value="card.value"
              :hint="card.hint"
              :icon="card.icon"
            />
          </div>
        </div>
      </div>

      <div :class="pageSectionDivideClass">
        <div v-if="statsLoading || statsError || !stats">
          <BaseState
            v-if="statsLoading"
            variant="loading"
            :title="t('cases.stats.loading')"
          />
          <BaseState
            v-else-if="statsError"
            variant="error"
            :title="t('common.status.error')"
            :message="statsError"
            :retry-text="t('common.actions.retry')"
            @retry="loadStats"
          />
          <BaseState
            v-else
            variant="empty"
            :title="t('cases.stats.empty')"
            :message="t('cases.stats.emptyHint')"
          />
        </div>

        <div v-else :class="grid12Class">
          <div :class="colSpan12Xl6">
            <div :class="casesDistributionItemClass">
              <div :class="[panelTitleClass, 'mb-2']">{{ t('cases.stats.priorityDistribution') }}</div>
              <div v-if="!priorityBreakdown.length" :class="panelSubtitleClass">{{ t('cases.stats.emptyDistribution') }}</div>
              <div v-else class="flex flex-wrap gap-2">
                <TpTag
                  v-for="item in priorityBreakdown"
                  :key="item.key"
                  variant="neutral"
                >
                  {{ item.label }}: {{ item.value }}
                </TpTag>
              </div>
            </div>
          </div>
          <div :class="colSpan12Xl6">
            <div :class="casesDistributionItemClass">
              <div :class="[panelTitleClass, 'mb-2']">{{ t('cases.stats.categoryDistribution') }}</div>
              <div v-if="!categoryBreakdown.length" :class="panelSubtitleClass">{{ t('cases.stats.emptyDistribution') }}</div>
              <div v-else class="flex flex-wrap gap-2">
                <TpTag
                  v-for="item in categoryBreakdown"
                  :key="item.key"
                  variant="neutral"
                >
                  {{ item.label }}: {{ item.value }}
                </TpTag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div :class="pageSectionDivideClass">
        <TableToolbar :title="t('cases.filters.title')">
          <template #actions>
            <span :class="tableToolbarSubtitle()">
              {{ t('cases.filters.selectedCount', { count: selectedCaseIds.length }) }}
            </span>
            <TpButton
              variant="danger"
              size="sm"
              :disabled="selectedCaseIds.length === 0 || listLoading || generateLoading || batchLoading"
              @click="openDeleteSelectedConfirm"
            >
              {{ t('cases.actions.deleteSelected') }}
            </TpButton>
          </template>
          <template #filters>
            <TableFilterForm @submit="handleSearch">
              <TableFilterInput
                v-model="filters.search"
                :placeholder="t('cases.filters.keywordPlaceholder')"
                :aria-label="t('cases.filters.keywordLabel')"
              />
              <TableFilterSelect
                v-model="filters.priority"
                :aria-label="t('cases.filters.priorityLabel')"
              >
                <option value="">{{ t('cases.filters.priorityAll') }}</option>
                <option v-for="option in priorityOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </TableFilterSelect>
              <TableFilterSelect v-model="filters.status" :aria-label="t('cases.filters.statusLabel')">
                <option value="">{{ t('cases.filters.statusAll') }}</option>
                <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </TableFilterSelect>
              <TableFilterSelect v-model="filters.category" :aria-label="t('cases.filters.categoryLabel')">
                <option value="">{{ t('cases.filters.categoryAll') }}</option>
                <option v-for="option in categoryOptions" :key="`filter-cat-${option.value}`" :value="option.value">
                  {{ option.label }}
                </option>
              </TableFilterSelect>
              <TpButton type="submit" :loading="listLoading">
                {{ t('cases.filters.apply') }}
              </TpButton>
            </TableFilterForm>
          </template>
        </TableToolbar>
      </div>

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
        :columns="tableColumns"
        :data="cases"
        :row-class="resolveCaseRowClass"
        :loading="listLoading"
        keep-content-while-loading
        :loading-title="t('cases.table.loading')"
        :empty-title="t('cases.table.empty')"
        :empty-message="''"
        :selectable="true"
        :selected-keys="selectedCaseIds"
        row-key="case_id"
        @update:selectedKeys="handleSelectionUpdate"
      >
        <template #toolbar>
          <TableToolbar :title="t('cases.table.title')" :pagination="pagination" />
        </template>
        <template #cell-caseId="{ row }">
          <div :class="[dataTitleClass, casesCellClamp2Class]" :title="resolveCaseId(row as CaseRecord)">
            {{ resolveCaseId(row as CaseRecord) }}
          </div>
        </template>
        <template #cell-title="{ row }">
          <div :class="[dataTitleClass, casesCellClamp3Class]" :title="(row as CaseRecord).title">
            {{ (row as CaseRecord).title }}
          </div>
          <div
            v-if="(row as CaseRecord).description"
            :class="[dataSubtitleDenseClass, casesCellMetaClass]"
            :title="(row as CaseRecord).description || undefined"
          >
            {{ (row as CaseRecord).description }}
          </div>
        </template>
        <template #cell-priority="{ row }">
          <TpTag :variant="casePriorityTagVariant((row as CaseRecord).priority)">
            {{ resolvePriorityLabel((row as CaseRecord).priority) }}
          </TpTag>
        </template>
        <template #cell-status="{ row }">
          <TpTag :variant="caseStatusTagVariant((row as CaseRecord).status)">
            {{ resolveStatusLabel((row as CaseRecord).status) }}
          </TpTag>
        </template>
        <template #cell-category="{ row }">
          {{ resolveCategoryLabel((row as CaseRecord).category) }}
        </template>
        <template #cell-testMethod="{ row }">
          {{ resolveTestMethodLabel((row as CaseRecord).test_method) }}
        </template>
        <template #cell-module="{ row }">
          <div
            :class="[dataSubtitleDenseClass, casesCellMetaClass]"
            :title="resolveModuleLabel((row as CaseRecord).module)"
          >
            {{ resolveModuleLabel((row as CaseRecord).module) }}
          </div>
        </template>
        <template #cell-tags="{ row }">
          <div
            :class="[dataSubtitleDenseClass, casesCellMetaClass]"
            :title="resolveTagsLabel((row as CaseRecord).tags)"
          >
            {{ resolveTagsLabel((row as CaseRecord).tags) }}
          </div>
        </template>
        <template #cell-steps="{ row }">
          <div
            :class="[dataSubtitleDenseClass, casesCellMetaClass]"
            :title="resolveStepsPreview(row as CaseRecord)"
          >
            {{ resolveStepsPreview(row as CaseRecord) }}
          </div>
        </template>
        <template #cell-updatedAt="{ row }">
          {{ formatCaseDateTime((row as CaseRecord).updated_time || (row as CaseRecord).created_time) }}
        </template>
        <template #cell-actions="{ row }">
          <div :class="casesActionsClass">
            <TpButton variant="primary" size="sm" @click.stop="openCaseEditor(row as CaseRecord)">
              {{ t('cases.table.actions.edit') }}
            </TpButton>
            <TpButton variant="ai" size="sm" :disabled="generateLoading" @click.stop="openRowGenerateConfirm(row as CaseRecord)">
              {{ t('cases.table.actions.regenerate') }}
            </TpButton>
            <TpButton variant="secondary" size="sm" :disabled="exporting" @click.stop="exportSingle(row as CaseRecord)">
              {{ t('cases.table.actions.exportOne') }}
            </TpButton>
            <TpButton variant="danger" size="sm" :disabled="listLoading || generateLoading || batchLoading" @click.stop="openDeleteConfirm(row as CaseRecord)">
              {{ t('cases.table.actions.deleteOne') }}
            </TpButton>
          </div>
        </template>
        <template #footer>
          <ListTablePager :pagination="pagination" :loading="listLoading" @change="changePage" />
        </template>
      </BaseTable>
      </div>
    </PagePanel>

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

    <CaseEditDrawer
      :visible="caseEditVisible"
      :record="editingCase"
      :priority-options="priorityOptions"
      :status-options="statusOptions"
      @close="closeCaseEditor"
      @saved="handleCaseSaved"
      @error="(message) => showNotice('danger', t('common.status.error'), message)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router';
import { usePageNotifier } from '@/composables/usePageNotifier';
import { resolveCaseCategoryDisplayName } from '@/utils/caseCategoryI18n';
import BaseState from '@/components/common/BaseState.vue';
import KnowledgeStatsCard from '@/components/common/KnowledgeStatsCard.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import ToolbarOverflowMenu from '@/components/common/ToolbarOverflowMenu.vue';
import {
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { TableFilterForm, TableFilterInput, TableFilterSelect } from '@/components/common/table';
import {
  dataSubtitleDenseClass,
  dataTitleClass,
  sectionTitleClass
} from '@/lib/page-typography';
import { statsSummaryPanelClass } from '@/lib/stats-ui';
import { type ListFetchMode } from '@/lib/list-fetch-mode';
import { casePriorityTagVariant, caseStatusTagVariant } from '@/lib/enum-tag-ui';
import { useListPageChange } from '@/composables/useListPageChange';
import { usePaginatedList } from '@/composables/usePaginatedList';
import { useTimedHighlight } from '@/composables/useTimedHighlight';
import ListTablePager from '@/components/common/ListTablePager.vue';
import { useConfirmAction } from '@/composables/useConfirmAction';
import { formatDateTime } from '@/lib/format';
import { triggerBlobDownload } from '@/lib/download';
import { formActionsClass, pageToolbarStripClass } from '@/lib/page-chrome-ui';
import {
  casesDistributionItemClass,
  colSpan12Md6,
  colSpan12Md6Min1400_3,
  colSpan12Xl6,
  grid12Class,
  pageMarkerCases,
  pageRootMarkedClass,
  pageSectionDivideClass
} from '@/lib/page-layout-ui';
import {
  casesActionsClass,
  casesCellClamp2Class,
  casesCellClamp3Class,
  casesCellMetaClass,
  casesExportFormatClass,
  casesRowHighlightClass,
  casesSyncHighlightClass
} from '@/lib/cases-ui';
import { parseBatchRequirementText } from '@/lib/cases-batch-requirements';
import { selectVariants } from '@/lib/field-control';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { panelSubtitleClass, panelTitleClass } from '@/lib/panel-ui';
import { tableToolbarSubtitle } from '@/lib/table-ui';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import CaseEditDrawer from '@/components/cases/CaseEditDrawer.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  batchGenerateCases,
  deleteCase,
  downloadCasesTemplate,
  exportCases,
  generateCases,
  getCaseConfig,
  getCaseStats,
  listCases,
  type CaseBatchGeneratePayload,
  type CaseBatchGenerateResult,
  type CaseGeneratePayload,
  type CaseGenerateResult,
  type CaseGenerationConfig,
  type CaseExportFormat,
  type CaseRecord,
  type CaseStats,
  type CaseProcessMode
} from '@/api/cases';

interface SelectOption {
  value: string;
  label: string;
}

interface CountOption {
  value: number;
  label: string;
}

interface PendingActionState {
  action: 'generate' | 'batchGenerate' | 'regenerate' | 'delete' | 'deleteBatch' | null;
  payload?: CaseGeneratePayload | CaseBatchGeneratePayload;
  row?: CaseRecord | null;
}

const props = withDefaults(defineProps<{
  mode?: 'generate' | 'manage';
}>(), {
  mode: 'manage'
});

const { t, locale } = useI18n();
const casesDateLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'));

function formatCaseDateTime(value: string | null | undefined) {
  return formatDateTime(value, casesDateLocale.value);
}
const router = useRouter();
const route = useRoute();
const cases = ref<CaseRecord[]>([]);
const stats = ref<CaseStats | null>(null);
const config = ref<CaseGenerationConfig | null>(null);
const lastGenerationResult = ref<CaseGenerateResult | CaseBatchGenerateResult | null>(null);
const selectedCaseIds = ref<Array<string | number>>([]);
const listRefreshLoading = ref(false);
const statsLoading = ref(false);
const generateLoading = ref(false);
const batchLoading = ref(false);
const exporting = ref(false);
const templateDownloading = ref(false);
const statsError = ref('');
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  showNotice: notifyShowNotice
} = usePageNotifier();
const manageSyncedTimer = ref<number | null>(null);
const manageSyncedHighlight = ref(false);
const caseRowHighlight = useTimedHighlight(4600);
type GenerateKind = 'single' | 'batch';

const generateKind = ref<GenerateKind>('single');
const pendingAction = ref<PendingActionState>({ action: null, payload: undefined, row: null });
const exportFormat = ref<CaseExportFormat>('excel');
const isGenerateMode = computed(() => props.mode === 'generate');
const isManageMode = computed(() => props.mode === 'manage');

const filters = reactive({
  search: '',
  priority: '',
  status: '',
  category: '',
  page: 1,
  per_page: 10
});

const singleForm = reactive({
  requirementText: '',
  caseCount: 5
});

const batchForm = reactive({
  requirementsText: '',
  caseCountPerRequirement: 3,
  processMode: 'sequential' as CaseProcessMode
});

const singleRequirementError = ref('');
const batchRequirementsError = ref('');

const pagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

const { listLoading, listError, loadPage: loadCasesPage } = usePaginatedList(cases, {
  refreshLoading: listRefreshLoading,
  pagination
});

const confirmDialog = useConfirmAction(t('common.actions.cancel'));

const caseCountOptions = computed<CountOption[]>(() => {
  const options = config.value?.case_count_options || [];
  if (options.length > 0) {
    return options.map((option) => ({
      value: option.value,
      label: t('cases.form.caseCountOption', { count: option.value })
    }));
  }
  return [1, 3, 5, 8, 10, 15, 20].map((value) => ({
    value,
    label: t('cases.form.caseCountOption', { count: value })
  }));
});

const categoryOptions = computed<SelectOption[]>(() => {
  const options = config.value?.test_type_options || [];
  if (options.length > 0) {
    return options.map((option) => ({
      value: option.value,
      label: translateEnum(`enums.cases.category.${option.value}`, option.label || option.value)
    }));
  }
  return [
    { value: 'functional', label: translateEnum('enums.cases.category.functional', 'Functional') },
    { value: 'performance', label: translateEnum('enums.cases.category.performance', 'Performance') },
    { value: 'security', label: translateEnum('enums.cases.category.security', 'Security') },
    { value: 'compatibility', label: translateEnum('enums.cases.category.compatibility', 'Compatibility') },
    { value: 'usability', label: translateEnum('enums.cases.category.usability', 'Usability') },
    { value: 'integration', label: translateEnum('enums.cases.category.integration', 'Integration') },
    { value: 'regression', label: translateEnum('enums.cases.category.regression', 'Regression') }
  ];
});

const priorityOptions = computed<SelectOption[]>(() => [
  { value: 'P0', label: translateEnum('enums.cases.priority.P0', 'P0') },
  { value: 'P1', label: translateEnum('enums.cases.priority.P1', 'P1') },
  { value: 'P2', label: translateEnum('enums.cases.priority.P2', 'P2') },
  { value: 'P3', label: translateEnum('enums.cases.priority.P3', 'P3') },
  { value: 'P4', label: translateEnum('enums.cases.priority.P4', 'P4') }
]);

const statusOptions = computed<SelectOption[]>(() => [
  { value: 'draft', label: translateEnum('enums.cases.status.draft', 'Draft') },
  { value: 'active', label: translateEnum('enums.cases.status.active', 'Active') },
  { value: 'deprecated', label: translateEnum('enums.cases.status.deprecated', 'Deprecated') }
]);

const processModeOptions = computed<SelectOption[]>(() => [
  { value: 'sequential', label: translateEnum('enums.cases.processMode.sequential', 'Sequential') },
  { value: 'parallel', label: translateEnum('enums.cases.processMode.parallel', 'Parallel') }
]);

const tableColumns = computed<BaseTableColumn[]>(() => [
  { key: 'caseId', label: t('cases.table.columns.caseId'), width: '260px' },
  { key: 'title', label: t('cases.table.columns.title'), width: '320px' },
  { key: 'priority', label: t('cases.table.columns.priority'), width: '110px' },
  { key: 'status', label: t('cases.table.columns.status'), width: '110px' },
  { key: 'category', label: t('cases.table.columns.category'), width: '120px' },
  { key: 'testMethod', label: t('cases.table.columns.testMethod'), width: '150px' },
  { key: 'module', label: t('cases.table.columns.module'), width: '180px' },
  { key: 'tags', label: t('cases.table.columns.tags'), width: '240px' },
  { key: 'steps', label: t('cases.table.columns.steps'), width: '320px' },
  { key: 'updatedAt', label: t('cases.table.columns.updatedAt'), width: '160px' },
  { key: 'actions', label: t('cases.table.columns.actions'), width: '300px', headerClass: 'text-end', cellClass: 'text-end' }
]);

const caseEditVisible = ref(false);
const editingCase = ref<CaseRecord | null>(null);

const statsCards = computed(() => [
  {
    key: 'total',
    label: t('cases.stats.total'),
    value: formatNumber(stats.value?.total_cases ?? 0),
    hint: t('cases.stats.totalHint'),
    icon: 'TC'
  },
  {
    key: 'draft',
    label: t('cases.stats.draft'),
    value: formatNumber(stats.value?.by_status?.draft ?? 0),
    hint: t('cases.stats.statusHint'),
    icon: 'DR'
  },
  {
    key: 'active',
    label: t('cases.stats.active'),
    value: formatNumber(stats.value?.by_status?.active ?? 0),
    hint: t('cases.stats.statusHint'),
    icon: 'OK'
  },
  {
    key: 'deprecated',
    label: t('cases.stats.deprecated'),
    value: formatNumber(stats.value?.by_status?.deprecated ?? 0),
    hint: t('cases.stats.statusHint'),
    icon: 'AR'
  }
]);

const priorityBreakdown = computed(() => {
  const source = stats.value?.by_priority || {};
  return Object.entries(source)
    .map(([key, value]) => ({
      key,
      label: translatePriority(key),
      value: Number(value || 0)
    }))
    .filter((item) => item.value > 0)
    .sort((left, right) => prioritySort(left.key, right.key));
});

const categoryBreakdown = computed(() => {
  const source = stats.value?.by_category || {};
  return Object.entries(source)
    .map(([key, value]) => ({
      key,
      label: translateCategory(key),
      value: Number(value || 0)
    }))
    .filter((item) => item.value > 0)
    .sort((left, right) => left.label.localeCompare(right.label));
});

function translateEnum(key: string, fallback: string) {
  const translated = t(key);
  return translated === key ? fallback : translated;
}

const TEST_METHOD_ALIASES: Record<string, string> = {
  '等价类划分法': 'Equivalence Partitioning',
  'equivalence partitioning': 'Equivalence Partitioning',
  '边界值分析法': 'Boundary Value Analysis',
  'boundary value analysis': 'Boundary Value Analysis',
  '因果图法': 'Cause-Effect Graphing',
  'cause-effect graphing': 'Cause-Effect Graphing',
  '判定表法': 'Decision Table Testing',
  'decision table testing': 'Decision Table Testing',
  '正交试验法': 'Orthogonal Array Testing',
  'orthogonal array testing': 'Orthogonal Array Testing',
  '状态迁移测试': 'State Transition Testing',
  'state transition testing': 'State Transition Testing'
};

function translatePriority(value: string) {
  return translateEnum(`enums.cases.priority.${value}`, value);
}

function translateStatus(value: string | undefined) {
  if (!value) return '-';
  return translateEnum(`enums.cases.status.${value}`, value);
}

function translateCategory(value: string | undefined) {
  if (!value) return '-';
  return resolveCaseCategoryDisplayName(value, t);
}

function translateTestMethod(value: string | undefined) {
  if (!value) return '-';
  const normalized = TEST_METHOD_ALIASES[value] || TEST_METHOD_ALIASES[value.toLowerCase()];
  if (!normalized) return value;
  return locale.value === 'en' ? normalized : value in TEST_METHOD_ALIASES ? value : (
    Object.entries(TEST_METHOD_ALIASES).find(([, enName]) => enName === normalized)?.[0] || value
  );
}

function prioritySort(left: string, right: string) {
  const order: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
  return (order[left] ?? 99) - (order[right] ?? 99);
}

function resolvePriorityLabel(priority: string | undefined) {
  if (!priority) return '-';
  return translatePriority(priority);
}

function resolveStatusLabel(status: string | undefined) {
  return translateStatus(status);
}

function resolveCategoryLabel(category: string | undefined) {
  return translateCategory(category);
}

function resolveTestMethodLabel(testMethod: string | undefined) {
  return translateTestMethod(testMethod);
}

function resolveModuleLabel(module: string | undefined) {
  return module?.trim() || '-';
}

function resolveTagsLabel(tags: string[] | undefined) {
  if (!Array.isArray(tags) || !tags.length) return '-';
  return tags.join(', ');
}

function resolveCaseId(caseItem: CaseRecord) {
  return caseItem.display_id || caseItem.case_id || '-';
}

function resolveStepsPreview(caseItem: CaseRecord) {
  const steps = Array.isArray(caseItem.steps) ? caseItem.steps : [];
  if (!steps.length) return t('cases.table.noSteps');
  return t('cases.table.stepsPreview', { count: steps.length, sample: steps[0] });
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(locale.value === 'en' ? 'en-US' : 'zh-CN').format(value);
}

function formatMetric(value: number | string | undefined | null) {
  if (value === undefined || value === null || value === '') return '-';
  if (typeof value === 'number' && Number.isFinite(value)) return value.toFixed(2);
  const next = Number(value);
  return Number.isFinite(next) ? next.toFixed(2) : String(value);
}

function formatBoolean(value: boolean | undefined) {
  if (value === undefined) return '-';
  return value ? t('common.boolean.yes') : t('common.boolean.no');
}

function showNotice(type: 'success' | 'danger' | 'warning' | 'info', title: string, message: string) {
  notifyShowNotice(type, message, { title });
}

function syncGenerateKindFromRoute() {
  if (!isGenerateMode.value) return;
  const kind = typeof route.query.kind === 'string' ? route.query.kind : '';
  generateKind.value = kind === 'batch' ? 'batch' : 'single';
  const prefill = typeof route.query.prefill === 'string' ? route.query.prefill.trim() : '';
  if (prefill && generateKind.value === 'single' && !singleForm.requirementText.trim()) {
    singleForm.requirementText = prefill;
  }
}

function resetSingleForm() {
  singleForm.requirementText = '';
  singleForm.caseCount = config.value?.default_case_count || 5;
}

function clearSingleRequirementInput() {
  singleForm.requirementText = '';
}

function resetBatchForm() {
  batchForm.requirementsText = '';
  batchForm.caseCountPerRequirement = Math.max(1, Math.min(3, config.value?.default_case_count || 3));
  batchForm.processMode = 'sequential';
}

function applyConfigDefaults() {
  const defaultCaseCount = config.value?.default_case_count || 5;
  singleForm.caseCount = defaultCaseCount;
  batchForm.caseCountPerRequirement = Math.max(1, Math.min(defaultCaseCount, config.value?.max_case_num || defaultCaseCount));
}

async function loadConfig() {
  try {
    config.value = await getCaseConfig();
    applyConfigDefaults();
  } catch (error) {
    config.value = null;
    showNotice('warning', t('common.feedback.warning'), getUserFacingErrorMessage(error, t('cases.message.configFailed')));
  }
}

async function loadStats() {
  try {
    statsLoading.value = true;
    statsError.value = '';
    stats.value = await getCaseStats();
  } catch (error) {
    statsError.value = getUserFacingErrorMessage(error, t('cases.message.statsFailed'));
    stats.value = null;
  } finally {
    statsLoading.value = false;
  }
}

async function loadCasesData(mode: ListFetchMode = 'page') {
  const result = await loadCasesPage(
    filters.page,
    mode,
    () =>
      listCases({
        page: filters.page,
        per_page: filters.per_page,
        search: filters.search,
        priority: filters.priority,
        status: filters.status,
        category: filters.category
      }).then((response) => ({ rows: response.cases, pagination: response.pagination })),
    {
      resolveMessage: (error) => getUserFacingErrorMessage(error, t('cases.message.loadFailed')),
      onClear: () => {
        cases.value = [];
      }
    }
  );
  if (result) {
    selectedCaseIds.value = selectedCaseIds.value.filter((id) => cases.value.some((item) => item.case_id === id));
  }
}

const { changePage } = useListPageChange(
  pagination,
  (_page, mode) => loadCasesData(mode),
  { onAcceptPage: (page) => { filters.page = page; } }
);

async function refreshAll(listMode: ListFetchMode = 'page') {
  await Promise.all([loadStats(), loadCasesData(listMode)]);
}

async function consumeGenerationRouteState() {
  if (!isManageMode.value) return;
  const from = typeof route.query.from === 'string' ? route.query.from : '';
  if (from !== 'generate' && from !== 'batchGenerate') return;

  // 生成后统一回到管理第一页；列表由 bootstrap/refresh 已加载，此处仅在需要检索定位时再请求
  filters.page = 1;
  const highlightQuery = typeof route.query.hids === 'string' ? route.query.hids : '';
  const idsFromQuery = highlightQuery
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
  const visibleIds = new Set(
    cases.value.flatMap((item) => [String(item.case_id || '').trim(), String(item.display_id || '').trim()]).filter(Boolean)
  );
  const hasVisibleTarget = idsFromQuery.some((id) => visibleIds.has(id));
  if (idsFromQuery.length && !hasVisibleTarget) {
    // 目标不在当前页/筛选结果时，自动按首个ID检索定位，避免“已跳转但无高亮”的错觉。
    filters.search = idsFromQuery[0];
    filters.page = 1;
    await loadCasesData('filter');
  }
  highlightRows(idsFromQuery);
  manageSyncedHighlight.value = true;
  if (manageSyncedTimer.value !== null) {
    window.clearTimeout(manageSyncedTimer.value);
  }
  manageSyncedTimer.value = window.setTimeout(() => {
    manageSyncedHighlight.value = false;
    manageSyncedTimer.value = null;
  }, 3800);

  showNotice(
    'warning',
    t('common.feedback.success'),
    from === 'batchGenerate' ? t('cases.message.batchGenerateSynced') : t('cases.message.generateSynced')
  );

  const nextQuery: LocationQueryRaw = { ...route.query };
  delete nextQuery.from;
  delete nextQuery.at;
  delete nextQuery.hids;
  await router.replace({ path: route.path, query: nextQuery });
}

function highlightRows(caseIds: string[]) {
  if (!isManageMode.value || !caseIds.length) return;
  caseRowHighlight.highlight(caseIds);
}

function resolveCaseRowClass(row: CaseRecord) {
  const caseId = String(row.case_id || '').trim();
  const displayId = String(row.display_id || '').trim();
  if (!caseId && !displayId) return '';
  return caseRowHighlight.has(caseId) || caseRowHighlight.has(displayId) ? casesRowHighlightClass : '';
}

async function handleRefresh() {
  await refreshAll('refresh');
  showNotice('success', t('common.feedback.success'), t('cases.message.refreshSuccess'));
}

function handleSearch() {
  filters.search = filters.search.trim();
  filters.page = 1;
  void loadCasesData('filter');
}

function handleSelectionUpdate(nextKeys: Array<string | number>) {
  selectedCaseIds.value = nextKeys;
}

function openGenerateConfirm() {
  const requirementText = singleForm.requirementText.trim();
  singleRequirementError.value = '';
  if (!requirementText) {
    singleRequirementError.value = t('cases.message.requirementRequired');
    return;
  }

  pendingAction.value = {
    action: 'generate',
    payload: {
      requirement_text: requirementText,
      case_count: singleForm.caseCount
    }
  };

  confirmDialog.open({
    title: t('cases.confirm.generateTitle'),
    message: t('cases.confirm.generateMessage', { count: singleForm.caseCount }),
    confirmText: t('cases.actions.generate'),
    variant: 'primary',
    onConfirm: runConfirmedAction
  });
}

function openBatchConfirm() {
  batchRequirementsError.value = '';
  const requirements = parseBatchRequirementText(batchForm.requirementsText);
  if (!requirements.length) {
    batchRequirementsError.value = t('cases.message.requirementsRequired');
    return;
  }

  pendingAction.value = {
    action: 'batchGenerate',
    payload: {
      requirements,
      case_count_per_req: batchForm.caseCountPerRequirement,
      process_mode: batchForm.processMode
    }
  };

  confirmDialog.open({
    title: t('cases.confirm.batchGenerateTitle'),
    message: t('cases.confirm.batchGenerateMessage', {
      count: requirements.length,
      mode: translateEnum(`enums.cases.processMode.${batchForm.processMode}`, batchForm.processMode)
    }),
    confirmText: t('cases.actions.batchGenerate'),
    variant: 'warning',
    onConfirm: runConfirmedAction
  });
}

function openCaseEditor(row: CaseRecord) {
  editingCase.value = row;
  caseEditVisible.value = true;
}

function closeCaseEditor() {
  caseEditVisible.value = false;
  editingCase.value = null;
}

async function handleCaseSaved(updated: CaseRecord) {
  closeCaseEditor();
  showNotice('success', t('common.feedback.success'), t('cases.message.updateSuccess'));
  const index = cases.value.findIndex((item) => item.case_id === updated.case_id);
  if (index >= 0) {
    cases.value[index] = updated;
  }
  await loadStats();
  highlightRows([updated.case_id]);
}

function openRowGenerateConfirm(row: CaseRecord) {
  const payload: CaseGeneratePayload = {
    requirement_text: buildRequirementFromCase(row),
    case_count: singleForm.caseCount
  };

  pendingAction.value = {
    action: 'regenerate',
    payload,
    row
  };

  confirmDialog.open({
    title: t('cases.confirm.regenerateTitle'),
    message: t('cases.confirm.regenerateMessage', { title: row.title }),
    confirmText: t('cases.table.actions.regenerate'),
    variant: 'primary',
    onConfirm: runConfirmedAction
  });
}

function openDeleteConfirm(row: CaseRecord) {
  pendingAction.value = {
    action: 'delete',
    payload: undefined,
    row
  };

  confirmDialog.open({
    title: t('cases.confirm.deleteTitle'),
    message: t('cases.confirm.deleteMessage', { title: row.title || row.case_id }),
    confirmText: t('cases.table.actions.deleteOne'),
    variant: 'danger',
    onConfirm: runConfirmedAction
  });
}

function openDeleteSelectedConfirm() {
  if (!selectedCaseIds.value.length) return;
  pendingAction.value = {
    action: 'deleteBatch',
    payload: undefined,
    row: null
  };

  confirmDialog.open({
    title: t('cases.confirm.deleteBatchTitle'),
    message: t('cases.confirm.deleteBatchMessage', { count: selectedCaseIds.value.length }),
    confirmText: t('cases.actions.deleteSelected'),
    variant: 'danger',
    onConfirm: runConfirmedAction
  });
}

async function runConfirmedAction() {
  const nextAction = pendingAction.value.action;
  const nextPayload = pendingAction.value.payload;
  const nextRow = pendingAction.value.row;
  pendingAction.value = { action: null, payload: undefined, row: null };

  if (!nextAction) return;

  if ((nextAction === 'generate' || nextAction === 'regenerate') && nextPayload) {
    await executeGenerate(nextPayload as CaseGeneratePayload);
  } else if (nextAction === 'batchGenerate' && nextPayload) {
    await executeBatchGenerate(nextPayload as CaseBatchGeneratePayload);
  } else if (nextAction === 'delete' && nextRow) {
    await executeDeleteCase(nextRow);
  } else if (nextAction === 'deleteBatch') {
    await executeDeleteSelectedCases();
  }
}

async function executeDeleteCase(row: CaseRecord) {
  if (!row.case_id) return;

  try {
    await deleteCase(row.case_id);
    selectedCaseIds.value = selectedCaseIds.value.filter((id) => String(id) !== String(row.case_id));
    showNotice('success', t('common.feedback.success'), t('cases.message.deleteSuccess'));
    await refreshAll('refresh');
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.deleteFailed')));
  }
}

async function executeDeleteSelectedCases() {
  const ids = [...selectedCaseIds.value].map((id) => String(id)).filter(Boolean);
  if (!ids.length) return;

  try {
    const results = await Promise.allSettled(ids.map((id) => deleteCase(id)));
    const successCount = results.filter((item) => item.status === 'fulfilled').length;
    const failedCount = ids.length - successCount;

    selectedCaseIds.value = [];
    await refreshAll('refresh');

    if (failedCount === 0) {
      showNotice('success', t('common.feedback.success'), t('cases.message.deleteBatchSuccess', { count: successCount }));
    } else {
      showNotice('warning', t('common.feedback.warning'), t('cases.message.deleteBatchPartial', {
        success: successCount,
        failed: failedCount
      }));
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.deleteBatchFailed')));
  }
}

async function executeGenerate(payload: CaseGeneratePayload) {
  try {
    generateLoading.value = true;
    const result = await generateCases(payload);
    lastGenerationResult.value = result;
    showNotice('success', t('common.feedback.success'), result.message || t('cases.message.generateSuccess', { count: result.total }));
    resetSingleForm();
    const highlightIds = result.cases.map((item) => String(item.case_id)).filter(Boolean);
    if (isGenerateMode.value) {
      await router.push({
        name: 'cases-manage',
        query: {
          from: 'generate',
          at: String(Date.now()),
          hids: highlightIds.slice(0, 12).join(',')
        }
      });
    } else {
      await refreshAll('refresh');
      highlightRows(highlightIds);
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.generateFailed')));
  } finally {
    generateLoading.value = false;
  }
}

async function executeBatchGenerate(payload: CaseBatchGeneratePayload) {
  try {
    batchLoading.value = true;
    const result = await batchGenerateCases(payload);
    lastGenerationResult.value = result;
    showNotice('success', t('common.feedback.success'), result.message || t('cases.message.batchGenerateSuccess', { count: result.total_cases }));
    resetBatchForm();
    const highlightIds = result.cases.map((item) => String(item.case_id)).filter(Boolean);
    if (isGenerateMode.value) {
      await router.push({
        name: 'cases-manage',
        query: {
          from: 'batchGenerate',
          at: String(Date.now()),
          hids: highlightIds.slice(0, 12).join(',')
        }
      });
    } else {
      await refreshAll('refresh');
      highlightRows(highlightIds);
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.batchGenerateFailed')));
  } finally {
    batchLoading.value = false;
  }
}

async function handleExport() {
  try {
    exporting.value = true;
    const payload = buildExportPayload();
    const result = await exportCases(payload, exportFormat.value);
    triggerBlobDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.exportSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.exportFailed')));
  } finally {
    exporting.value = false;
  }
}

async function handleDownloadTemplate() {
  try {
    templateDownloading.value = true;
    const result = await downloadCasesTemplate('excel');
    triggerBlobDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.templateDownloadSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.templateDownloadFailed')));
  } finally {
    templateDownloading.value = false;
  }
}

async function exportSingle(row: CaseRecord) {
  try {
    exporting.value = true;
    const result = await exportCases({ case_ids: [row.case_id] }, 'excel');
    triggerBlobDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.exportSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), getUserFacingErrorMessage(error, t('cases.message.exportFailed')));
  } finally {
    exporting.value = false;
  }
}

function buildExportPayload() {
  const payload: {
    category?: string;
    priority?: string;
    status?: string;
    search?: string;
    case_ids?: Array<string | number>;
  } = {};

  const total = Number(pagination.value.total || 0);
  const currentPageCount = cases.value.length;
  const selectedCount = selectedCaseIds.value.length;
  const isCurrentPageAllSelected = currentPageCount > 0 && selectedCount === currentPageCount;

  // UX约定：当“当前页全选”且列表还有跨页数据时，导出应覆盖当前筛选下的全部数据，而不是仅当前页。
  if (isCurrentPageAllSelected && total > currentPageCount) {
    if (filters.category) payload.category = filters.category;
    if (filters.priority) payload.priority = filters.priority;
    if (filters.status) payload.status = filters.status;
    if (filters.search) payload.search = filters.search;
    return payload;
  }

  if (selectedCaseIds.value.length > 0) {
    payload.case_ids = [...selectedCaseIds.value];
    return payload;
  }

  if (filters.category) payload.category = filters.category;
  if (filters.priority) payload.priority = filters.priority;
  if (filters.status) payload.status = filters.status;
  if (filters.search) payload.search = filters.search;
  return payload;
}

function buildRequirementFromCase(row: CaseRecord) {
  const parts = [
    row.title,
    row.description,
    row.precondition,
    Array.isArray(row.steps) ? row.steps.join('\n') : '',
    Array.isArray(row.expected_result) ? row.expected_result.join('\n') : ''
  ];
  return parts.filter(Boolean).join('\n');
}

function applyConfigFallbacks() {
  if (!singleForm.caseCount) {
    singleForm.caseCount = config.value?.default_case_count || 5;
  }
  if (!batchForm.caseCountPerRequirement) {
    batchForm.caseCountPerRequirement = Math.max(1, config.value?.default_case_count || 3);
  }
}

async function bootstrapManageMode() {
  await refreshAll('initial');
  await consumeGenerationRouteState();
}

onMounted(async () => {
  await loadConfig();
  applyConfigFallbacks();
  if (isManageMode.value) {
    await bootstrapManageMode();
  } else {
    syncGenerateKindFromRoute();
  }
});

watch(
  () => props.mode,
  async (mode) => {
    if (mode === 'manage') {
      await bootstrapManageMode();
    } else {
      syncGenerateKindFromRoute();
    }
  }
);

watch(
  () => route.query.kind,
  () => {
    syncGenerateKindFromRoute();
  }
);

onBeforeUnmount(() => {
  if (manageSyncedTimer.value !== null) {
    window.clearTimeout(manageSyncedTimer.value);
    manageSyncedTimer.value = null;
  }
});
</script>
