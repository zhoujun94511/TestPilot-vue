<template>
  <section class="tp-container-fluid tp-py-3 tp-page tp-page-shell tp-cases-page">
    <div v-if="notice" class="tp-risk-block tp-cases-toast" :class="noticeClass" role="status" aria-live="polite">
      <div class="tp-flex-grow-1">
        <div class="tp-risk-block__title">{{ notice.title }}</div>
        <div class="tp-risk-block__text">{{ notice.message }}</div>
      </div>
      <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="clearNotice">
        {{ t('common.actions.close') }}
      </TpButton>
    </div>

    <div v-if="isManageMode" class="tp-surface tp-p-3 tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-justify-end tp-align-center tp-gap-2">
        <template v-if="isManageMode">
          <select v-model="exportFormat" class="tp-select tp-cases-export-format">
            <option value="excel">{{ t('cases.actions.exportExcel') }}</option>
            <option value="csv">{{ t('cases.actions.exportCsv') }}</option>
            <option value="json">{{ t('cases.actions.exportJson') }}</option>
          </select>
          <TpButton variant="success" :loading="exporting" @click="handleExport">
            {{ exporting ? t('cases.actions.exporting') : t('cases.actions.export') }}
          </TpButton>
          <TpButton variant="ghost" :loading="templateDownloading" @click="handleDownloadTemplate">
            {{ templateDownloading ? t('cases.actions.templateDownloading') : t('cases.actions.downloadTemplate') }}
          </TpButton>
        </template>
        <TpButton variant="secondary" :loading="listLoading || statsLoading" @click="handleRefresh">
          {{ t('cases.actions.refresh') }}
        </TpButton>
      </div>
    </div>

    <div v-if="isGenerateMode && showSinglePanel" class="tp-surface tp-p-3 tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
        <div>
          <div class="tp-card__title">{{ t('cases.single.title') }}</div>
          <div class="tp-card__subtitle">{{ t('cases.single.hint') }}</div>
          <div class="tp-cases-inline-count tp-mt-2">
            <label class="tp-form-label tp-mb-1">{{ t('cases.form.caseCountLabel') }}</label>
            <select v-model.number="singleForm.caseCount" class="tp-select">
              <option v-for="option in caseCountOptions" :key="`single-inline-${option.value}`" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>
        <div class="tp-card__subtitle tp-cases-panel-note">
          {{ t('cases.single.autoPriorityHint') }}
        </div>
      </div>

      <form class="tp-row tp-g-3" @submit.prevent="openGenerateConfirm">
        <div class="tp-col-12">
          <label class="tp-form-label">{{ t('cases.form.requirementLabel') }}</label>
          <textarea
            v-model.trim="singleForm.requirementText"
            class="tp-textarea"
            rows="6"
            :placeholder="t('cases.form.requirementPlaceholder')"
            required
          ></textarea>
        </div>


        <div class="tp-col-12 tp-flex tp-flex-wrap tp-justify-end tp-gap-2">
          <TpButton variant="ghost" type="button" @click="clearSingleRequirementInput">
            {{ t('cases.actions.clearInput') }}
          </TpButton>
          <TpButton variant="secondary" type="button" @click="resetSingleForm">
            {{ t('common.actions.cancel') }}
          </TpButton>
          <TpButton type="submit" :loading="generateLoading" :disabled="generateLoading || !singleForm.requirementText.trim()">
            {{ generateLoading ? t('cases.actions.generating') : t('cases.actions.generate') }}
          </TpButton>
        </div>
      </form>
    </div>

    <div v-if="isGenerateMode && showBatchPanel" class="tp-surface tp-p-3 tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
        <div>
          <div class="tp-card__title">{{ t('cases.batch.title') }}</div>
          <div class="tp-card__subtitle">{{ t('cases.batch.hint') }}</div>
        </div>
        <div class="tp-card__subtitle tp-cases-panel-note">
          {{ t('cases.batch.processHint') }}
        </div>
      </div>

      <form class="tp-row tp-g-3 tp-align-end" @submit.prevent="openBatchConfirm">
        <div class="tp-col-12">
          <label class="tp-form-label">{{ t('cases.batch.requirementsLabel') }}</label>
          <textarea
            v-model.trim="batchForm.requirementsText"
            class="tp-textarea"
            rows="6"
            :placeholder="t('cases.batch.requirementsPlaceholder')"
            required
          ></textarea>
        </div>

        <div class="tp-col-12 tp-col-md-4">
          <label class="tp-form-label">{{ t('cases.form.caseCountLabel') }}</label>
          <select v-model.number="batchForm.caseCountPerRequirement" class="tp-select">
            <option v-for="option in caseCountOptions" :key="`batch-${option.value}`" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="tp-col-12 tp-col-md-4">
          <label class="tp-form-label">{{ t('cases.batch.processModeLabel') }}</label>
          <select v-model="batchForm.processMode" class="tp-select">
            <option v-for="option in processModeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>


        <div class="tp-col-12 tp-flex tp-flex-wrap tp-justify-end tp-gap-2">
          <TpButton variant="secondary" type="button" @click="resetBatchForm">
            {{ t('common.actions.cancel') }}
          </TpButton>
          <TpButton type="submit" :loading="batchLoading" :disabled="batchLoading || !batchForm.requirementsText.trim()">
            {{ batchLoading ? t('cases.actions.batchGenerating') : t('cases.actions.batchGenerate') }}
          </TpButton>
        </div>
      </form>
    </div>

    <div v-if="isManageMode" class="tp-row tp-g-3 tp-mb-3">
      <div v-for="card in statsCards" :key="card.key" class="tp-col-12 tp-col-md-6 tp-col-xxl-3">
        <TpCard>
          <div class="tp-kpi-label">{{ card.label }}</div>
          <div class="tp-kpi-value">{{ card.value }}</div>
          <div v-if="card.hint" class="tp-kpi-hint">{{ card.hint }}</div>
        </TpCard>
      </div>
    </div>

    <div v-if="isManageMode" class="tp-surface tp-p-3 tp-mb-3">
      <div v-if="statsLoading || statsError || !stats" class="tp-mb-3">
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

      <div v-else class="tp-row tp-g-3 tp-cases-distribution-row">
        <div class="tp-col-12 tp-col-xl-6">
          <div class="tp-cases-distribution-item tp-p-3 tp-h-100">
            <div class="tp-card__title tp-mb-2">{{ t('cases.stats.priorityDistribution') }}</div>
            <div v-if="!priorityBreakdown.length" class="tp-card__subtitle">{{ t('cases.stats.emptyDistribution') }}</div>
            <div v-else class="tp-flex tp-flex-wrap tp-gap-2">
              <span
                v-for="item in priorityBreakdown"
                :key="item.key"
                class="tp-tag tp-tag--neutral"
              >
                {{ item.label }}: {{ item.value }}
              </span>
            </div>
          </div>
        </div>
        <div class="tp-col-12 tp-col-xl-6">
          <div class="tp-cases-distribution-item tp-p-3 tp-h-100">
            <div class="tp-card__title tp-mb-2">{{ t('cases.stats.categoryDistribution') }}</div>
            <div v-if="!categoryBreakdown.length" class="tp-card__subtitle">{{ t('cases.stats.emptyDistribution') }}</div>
            <div v-else class="tp-flex tp-flex-wrap tp-gap-2">
              <span
                v-for="item in categoryBreakdown"
                :key="item.key"
                class="tp-tag tp-tag--neutral"
              >
                {{ item.label }}: {{ item.value }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isManageMode" class="tp-surface tp-p-3 tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
        <div>
          <div class="tp-card__title">{{ t('cases.filters.title') }}</div>
          <div class="tp-card__subtitle">{{ paginationText }}</div>
        </div>
        <div class="tp-flex tp-flex-wrap tp-align-center tp-gap-2">
          <div class="tp-card__subtitle">
            {{ t('cases.filters.selectedCount', { count: selectedCaseIds.length }) }}
          </div>
          <TpButton
            variant="danger"
            size="sm"
            :disabled="selectedCaseIds.length === 0 || listLoading || generateLoading || batchLoading"
            @click="openDeleteSelectedConfirm"
          >
            {{ t('cases.actions.deleteSelected') }}
          </TpButton>
        </div>
      </div>

      <form class="tp-row tp-g-3 tp-align-end" @submit.prevent="handleSearch">
        <div class="tp-col-12 tp-col-lg-5">
          <label class="tp-form-label">{{ t('cases.filters.keywordLabel') }}</label>
          <input
            v-model.trim="filters.search"
            type="search"
            class="tp-input"
            :placeholder="t('cases.filters.keywordPlaceholder')"
          />
        </div>

        <div class="tp-col-12 tp-col-lg-2">
          <label class="tp-form-label">{{ t('cases.filters.priorityLabel') }}</label>
          <select v-model="filters.priority" class="tp-select">
            <option value="">{{ t('cases.filters.priorityAll') }}</option>
            <option v-for="option in priorityOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="tp-col-12 tp-col-lg-2">
          <label class="tp-form-label">{{ t('cases.filters.statusLabel') }}</label>
          <select v-model="filters.status" class="tp-select">
            <option value="">{{ t('cases.filters.statusAll') }}</option>
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="tp-col-12 tp-col-lg-2">
          <label class="tp-form-label">{{ t('cases.filters.categoryLabel') }}</label>
          <select v-model="filters.category" class="tp-select">
            <option value="">{{ t('cases.filters.categoryAll') }}</option>
            <option v-for="option in categoryOptions" :key="`filter-cat-${option.value}`" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="tp-col-12 tp-col-lg-1 tp-grid">
          <TpButton type="submit" :loading="listLoading">
            {{ t('cases.filters.apply') }}
          </TpButton>
        </div>
      </form>
    </div>

    <div v-if="isManageMode" class="tp-surface tp-p-3" :class="{ 'tp-cases-sync-highlight': manageSyncedHighlight }">
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
        :columns="tableColumns"
        :data="cases"
        :row-class="resolveCaseRowClass"
        :loading="listLoading"
        :loading-title="t('cases.table.loading')"
        :empty-title="t('cases.table.empty')"
        :empty-message="''"
        :selectable="true"
        :selected-keys="selectedCaseIds"
        row-key="case_id"
        @update:selectedKeys="handleSelectionUpdate"
      >
        <template #cell-caseId="{ row }">
          <div class="tp-data-title tp-cases-cell-id" :title="resolveCaseId(row as CaseRecord)">
            {{ resolveCaseId(row as CaseRecord) }}
          </div>
        </template>
        <template #cell-title="{ row }">
          <div class="tp-data-title tp-cases-cell-title" :title="(row as CaseRecord).title">
            {{ (row as CaseRecord).title }}
          </div>
          <div v-if="(row as CaseRecord).description" class="tp-data-subtitle tp-cases-cell-desc">
            {{ (row as CaseRecord).description }}
          </div>
        </template>
        <template #cell-priority="{ row }">
          <TpTag :variant="priorityTagVariant((row as CaseRecord).priority)">
            {{ resolvePriorityLabel((row as CaseRecord).priority) }}
          </TpTag>
        </template>
        <template #cell-status="{ row }">
          <TpTag :variant="statusTagVariant((row as CaseRecord).status)">
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
          <div class="tp-data-subtitle tp-cases-cell-meta">{{ resolveModuleLabel((row as CaseRecord).module) }}</div>
        </template>
        <template #cell-tags="{ row }">
          <div class="tp-data-subtitle tp-cases-cell-meta">{{ resolveTagsLabel((row as CaseRecord).tags) }}</div>
        </template>
        <template #cell-steps="{ row }">
          <div class="tp-data-subtitle tp-cases-cell-steps">
            {{ resolveStepsPreview(row as CaseRecord) }}
          </div>
        </template>
        <template #cell-updatedAt="{ row }">
          {{ formatDateTime((row as CaseRecord).updated_time || (row as CaseRecord).created_time) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="tp-flex tp-justify-end tp-gap-2 tp-cases-actions">
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

    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :confirm-text="confirm.confirmText"
      :cancel-text="confirm.cancelText"
      :confirm-variant="confirm.variant"
      @confirm="runConfirmedAction"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
import { resolveCaseCategoryDisplayName } from '@/utils/caseCategoryI18n';
import BaseState from '@/components/common/BaseState.vue';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
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

interface NoticeState {
  type: 'success' | 'danger' | 'warning' | 'info';
  title: string;
  message: string;
}

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
const router = useRouter();
const route = useRoute();
const appStore = useAppStore();

const cases = ref<CaseRecord[]>([]);
const stats = ref<CaseStats | null>(null);
const config = ref<CaseGenerationConfig | null>(null);
const lastGenerationResult = ref<CaseGenerateResult | CaseBatchGenerateResult | null>(null);
const selectedCaseIds = ref<Array<string | number>>([]);
const listLoading = ref(false);
const statsLoading = ref(false);
const generateLoading = ref(false);
const batchLoading = ref(false);
const exporting = ref(false);
const templateDownloading = ref(false);
const listError = ref('');
const statsError = ref('');
const notice = ref<NoticeState | null>(null);
const noticeTimer = ref<number | null>(null);
const manageSyncedTimer = ref<number | null>(null);
const manageSyncedHighlight = ref(false);
const highlightCaseIds = ref<Set<string>>(new Set());
const highlightRowsTimer = ref<number | null>(null);
const showSinglePanel = ref(true);
const showBatchPanel = ref(false);
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
  caseCount: 5,
});

const batchForm = reactive({
  requirementsText: '',
  caseCountPerRequirement: 3,
  processMode: 'sequential' as CaseProcessMode
});

const pagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

const confirm = reactive({
  visible: false,
  title: '',
  message: '',
  confirmText: '',
  cancelText: t('common.actions.cancel'),
  variant: 'primary' as 'primary' | 'danger' | 'warning'
});

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
  { key: 'actions', label: t('cases.table.columns.actions'), width: '180px', headerClass: 'text-end', cellClass: 'text-end' }
]);

const statsCards = computed(() => [
  { key: 'total', label: t('cases.stats.total'), value: formatNumber(stats.value?.total_cases ?? 0), hint: t('cases.stats.totalHint') },
  { key: 'draft', label: t('cases.stats.draft'), value: formatNumber(stats.value?.by_status?.draft ?? 0), hint: t('cases.stats.statusHint') },
  { key: 'active', label: t('cases.stats.active'), value: formatNumber(stats.value?.by_status?.active ?? 0), hint: t('cases.stats.statusHint') },
  { key: 'deprecated', label: t('cases.stats.deprecated'), value: formatNumber(stats.value?.by_status?.deprecated ?? 0), hint: t('cases.stats.statusHint') }
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

const paginationText = computed(() => {
  const safePages = Math.max(1, pagination.value.pages || 0);
  const safePage = Math.min(Math.max(1, pagination.value.page || 1), safePages);
  return t('cases.pagination.pageInfo', {
    page: safePage,
    pages: safePages,
    total: formatNumber(pagination.value.total)
  });
});

const noticeClass = computed(() => {
  if (!notice.value) return '';
  return {
    'tp-risk-block--info': notice.value.type === 'info',
    'tp-risk-block--danger': notice.value.type === 'danger',
    'tp-risk-block--warning': notice.value.type === 'warning',
    'tp-risk-block--success': notice.value.type === 'success'
  };
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

function priorityTagVariant(priority: string | undefined) {
  switch (priority) {
    case 'P0':
      return 'danger';
    case 'P1':
      return 'warning';
    case 'P2':
      return 'info';
    case 'P3':
      return 'neutral';
    case 'P4':
      return 'neutral';
    default:
      return 'neutral';
  }
}

function statusTagVariant(status: string | undefined) {
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

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function showNotice(type: NoticeState['type'], title: string, message: string) {
  // 成功/信息类反馈不再打断页面，保留告警与错误即可
  if (type === 'success' || type === 'info') {
    return;
  }
  if (noticeTimer.value !== null) {
    window.clearTimeout(noticeTimer.value);
    noticeTimer.value = null;
  }
  notice.value = { type, title, message };
  const timeout = type === 'danger' ? 8000 : 5000;
  noticeTimer.value = window.setTimeout(() => {
    clearNotice();
  }, timeout);
}

function clearNotice() {
  if (noticeTimer.value !== null) {
    window.clearTimeout(noticeTimer.value);
    noticeTimer.value = null;
  }
  notice.value = null;
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
    showNotice('warning', t('common.feedback.warning'), error instanceof Error ? error.message : t('cases.message.configFailed'));
  }
}

async function loadStats() {
  try {
    statsLoading.value = true;
    statsError.value = '';
    stats.value = await getCaseStats();
  } catch (error) {
    statsError.value = error instanceof Error ? error.message : t('cases.message.statsFailed');
    stats.value = null;
  } finally {
    statsLoading.value = false;
  }
}

async function loadCasesData() {
  try {
    listLoading.value = true;
    listError.value = '';
    const response = await listCases({
      page: filters.page,
      per_page: filters.per_page,
      search: filters.search,
      priority: filters.priority,
      status: filters.status,
      category: filters.category
    });
    cases.value = response.cases;
    pagination.value = response.pagination;
    selectedCaseIds.value = selectedCaseIds.value.filter((id) => cases.value.some((item) => item.case_id === id));
  } catch (error) {
    listError.value = error instanceof Error ? error.message : t('cases.message.loadFailed');
    cases.value = [];
  } finally {
    listLoading.value = false;
  }
}

async function refreshAll() {
  await Promise.all([loadStats(), loadCasesData()]);
}

async function consumeGenerationRouteState() {
  if (!isManageMode.value) return;
  const from = typeof route.query.from === 'string' ? route.query.from : '';
  if (from !== 'generate' && from !== 'batchGenerate') return;

  // 生成后统一回到管理第一页，确保用户能看到最新新增结果
  filters.page = 1;
  await loadCasesData();
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
    await loadCasesData();
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

  const nextQuery = { ...route.query } as Record<string, unknown>;
  delete nextQuery.from;
  delete nextQuery.at;
  delete nextQuery.hids;
  await router.replace({ path: route.path, query: nextQuery });
}

function highlightRows(caseIds: string[]) {
  if (!isManageMode.value || !caseIds.length) return;
  highlightCaseIds.value = new Set(
    caseIds
      .map((id) => String(id || '').trim())
      .filter(Boolean)
      .slice(0, 12)
  );
  if (highlightRowsTimer.value !== null) {
    window.clearTimeout(highlightRowsTimer.value);
  }
  highlightRowsTimer.value = window.setTimeout(() => {
    highlightCaseIds.value = new Set();
    highlightRowsTimer.value = null;
  }, 4600);
}

function resolveCaseRowClass(row: Record<string, unknown>) {
  const caseId = String((row as CaseRecord).case_id || '').trim();
  const displayId = String((row as CaseRecord).display_id || '').trim();
  if (!caseId && !displayId) return '';
  return highlightCaseIds.value.has(caseId) || highlightCaseIds.value.has(displayId) ? 'tp-cases-row-highlight' : '';
}

async function handleRefresh() {
  await refreshAll();
  showNotice('success', t('common.feedback.success'), t('cases.message.refreshSuccess'));
}

function handleSearch() {
  filters.page = 1;
  loadCasesData();
}

function changePage(page: number) {
  filters.page = page;
  loadCasesData();
}

function handleSelectionUpdate(nextKeys: Array<string | number>) {
  selectedCaseIds.value = nextKeys;
}

function openGenerateConfirm() {
  const requirementText = singleForm.requirementText.trim();
  if (!requirementText) {
    showNotice('warning', t('common.feedback.warning'), t('cases.message.requirementRequired'));
    return;
  }

  pendingAction.value = {
    action: 'generate',
    payload: {
      requirement_text: requirementText,
      case_count: singleForm.caseCount
    }
  };

  confirm.title = t('cases.confirm.generateTitle');
  confirm.message = t('cases.confirm.generateMessage', { count: singleForm.caseCount });
  confirm.confirmText = t('cases.actions.generate');
  confirm.variant = 'primary';
  confirm.visible = true;
}

function openBatchConfirm() {
  const requirements = parseRequirements(batchForm.requirementsText);
  if (!requirements.length) {
    showNotice('warning', t('common.feedback.warning'), t('cases.message.requirementsRequired'));
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

  confirm.title = t('cases.confirm.batchGenerateTitle');
  confirm.message = t('cases.confirm.batchGenerateMessage', {
    count: requirements.length,
    mode: translateEnum(`enums.cases.processMode.${batchForm.processMode}`, batchForm.processMode)
  });
  confirm.confirmText = t('cases.actions.batchGenerate');
  confirm.variant = 'warning';
  confirm.visible = true;
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

  confirm.title = t('cases.confirm.regenerateTitle');
  confirm.message = t('cases.confirm.regenerateMessage', { title: row.title });
  confirm.confirmText = t('cases.table.actions.regenerate');
  confirm.variant = 'primary';
  confirm.visible = true;
}

function openDeleteConfirm(row: CaseRecord) {
  pendingAction.value = {
    action: 'delete',
    payload: undefined,
    row
  };

  confirm.title = t('cases.confirm.deleteTitle');
  confirm.message = t('cases.confirm.deleteMessage', { title: row.title || row.case_id });
  confirm.confirmText = t('cases.table.actions.deleteOne');
  confirm.variant = 'danger';
  confirm.visible = true;
}

function openDeleteSelectedConfirm() {
  if (!selectedCaseIds.value.length) return;
  pendingAction.value = {
    action: 'deleteBatch',
    payload: undefined,
    row: null
  };

  confirm.title = t('cases.confirm.deleteBatchTitle');
  confirm.message = t('cases.confirm.deleteBatchMessage', { count: selectedCaseIds.value.length });
  confirm.confirmText = t('cases.actions.deleteSelected');
  confirm.variant = 'danger';
  confirm.visible = true;
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
    listLoading.value = true;
    await deleteCase(row.case_id);
    selectedCaseIds.value = selectedCaseIds.value.filter((id) => String(id) !== String(row.case_id));
    showNotice('success', t('common.feedback.success'), t('cases.message.deleteSuccess'));
    await refreshAll();
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.deleteFailed'));
  } finally {
    listLoading.value = false;
  }
}

async function executeDeleteSelectedCases() {
  const ids = [...selectedCaseIds.value].map((id) => String(id)).filter(Boolean);
  if (!ids.length) return;

  try {
    listLoading.value = true;
    const results = await Promise.allSettled(ids.map((id) => deleteCase(id)));
    const successCount = results.filter((item) => item.status === 'fulfilled').length;
    const failedCount = ids.length - successCount;

    selectedCaseIds.value = [];
    await refreshAll();

    if (failedCount === 0) {
      showNotice('success', t('common.feedback.success'), t('cases.message.deleteBatchSuccess', { count: successCount }));
    } else {
      showNotice('warning', t('common.feedback.warning'), t('cases.message.deleteBatchPartial', {
        success: successCount,
        failed: failedCount
      }));
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.deleteBatchFailed'));
  } finally {
    listLoading.value = false;
  }
}

async function executeGenerate(payload: CaseGeneratePayload) {
  try {
    generateLoading.value = true;
    const result = await generateCases(payload);
    lastGenerationResult.value = result;
    showNotice('success', t('common.feedback.success'), result.message || t('cases.message.generateSuccess', { count: result.total }));
    resetSingleForm();
    await refreshAll();
    highlightRows(result.cases.map((item) => String(item.case_id)).filter(Boolean));
    if (isGenerateMode.value) {
      await router.push({
        name: 'cases-manage',
        query: {
          ...route.query,
          from: 'generate',
          at: String(Date.now()),
          hids: result.cases.map((item) => String(item.case_id)).filter(Boolean).slice(0, 12).join(',')
        }
      });
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.generateFailed'));
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
    await refreshAll();
    highlightRows(result.cases.map((item) => String(item.case_id)).filter(Boolean));
    if (isGenerateMode.value) {
      await router.push({
        name: 'cases-manage',
        query: {
          ...route.query,
          from: 'batchGenerate',
          at: String(Date.now()),
          hids: result.cases.map((item) => String(item.case_id)).filter(Boolean).slice(0, 12).join(',')
        }
      });
    }
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.batchGenerateFailed'));
  } finally {
    batchLoading.value = false;
  }
}

async function handleExport() {
  try {
    exporting.value = true;
    const payload = buildExportPayload();
    const result = await exportCases(payload, exportFormat.value);
    triggerDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.exportSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.exportFailed'));
  } finally {
    exporting.value = false;
  }
}

async function handleDownloadTemplate() {
  try {
    templateDownloading.value = true;
    const result = await downloadCasesTemplate('excel');
    triggerDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.templateDownloadSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.templateDownloadFailed'));
  } finally {
    templateDownloading.value = false;
  }
}

async function exportSingle(row: CaseRecord) {
  try {
    exporting.value = true;
    const result = await exportCases({ case_ids: [row.case_id] }, 'excel');
    triggerDownload(result.blob, result.filename);
    showNotice('success', t('common.feedback.success'), t('cases.message.exportSuccess'));
  } catch (error) {
    showNotice('danger', t('common.status.error'), error instanceof Error ? error.message : t('cases.message.exportFailed'));
  } finally {
    exporting.value = false;
  }
}

function buildExportPayload() {
  const payload: {
    category?: string;
    priority?: string;
    status?: string;
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

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'test_cases.xlsx';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function parseRequirements(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
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

onMounted(async () => {
  await loadConfig();
  applyConfigFallbacks();
  await refreshAll();
  await consumeGenerationRouteState();
});

watch(
  () => [route.query.from, route.query.hids, route.query.at],
  async () => {
    await consumeGenerationRouteState();
  }
);

onBeforeUnmount(() => {
  if (noticeTimer.value !== null) {
    window.clearTimeout(noticeTimer.value);
    noticeTimer.value = null;
  }
  if (manageSyncedTimer.value !== null) {
    window.clearTimeout(manageSyncedTimer.value);
    manageSyncedTimer.value = null;
  }
  if (highlightRowsTimer.value !== null) {
    window.clearTimeout(highlightRowsTimer.value);
    highlightRowsTimer.value = null;
  }
});
</script>

<style scoped>
.tp-cases-toast {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1100;
  width: min(460px, calc(100vw - 24px));
  box-shadow: var(--tp-shadow-md);
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.tp-cases-toast .flex-grow-1 {
  min-width: 0;
}

.tp-cases-toast :deep(.tp-btn) {
  flex: 0 0 auto;
}

.tp-cases-toast .tp-risk-block__text {
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 576px) {
  .tp-cases-toast {
    align-items: stretch;
    gap: 8px;
  }

  .tp-cases-toast :deep(.tp-btn) {
    align-self: flex-start;
  }
}

.tp-cases-panel-note {
  max-width: 260px;
}

.tp-cases-inline-count {
  max-width: 220px;
}

.tp-cases-sync-highlight {
  outline: 2px solid color-mix(in srgb, var(--tp-color-primary-500) 78%, transparent);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--tp-color-primary-500) 24%, transparent);
  transition: box-shadow 0.25s ease, outline-color 0.25s ease;
}

:deep(.tp-cases-row-highlight) {
  background: color-mix(in srgb, var(--tp-color-primary-500) 34%, transparent);
  animation: tp-cases-highlight-fade 4.6s ease forwards;
}

@keyframes tp-cases-highlight-fade {
  0% {
    background: color-mix(in srgb, var(--tp-color-primary-500) 42%, transparent);
  }
  100% {
    background: transparent;
  }
}

.tp-form-label--placeholder {
  visibility: hidden;
  margin-bottom: 6px;
}

.tp-cases-distribution-row {
  --bs-gutter-x: 12px;
  --bs-gutter-y: 12px;
  margin-left: 0;
  margin-right: 0;
}

.tp-cases-distribution-item {
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.tp-cases-cell-id {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
  overflow-wrap: anywhere;
  overflow: hidden;
  line-height: 1.45;
}

.tp-cases-cell-title {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.45;
}

.tp-cases-cell-desc,
.tp-cases-cell-steps,
.tp-cases-cell-meta {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.45;
  margin-top: 2px;
}

.tp-cases-actions {
  flex-wrap: nowrap;
}

.tp-cases-actions :deep(.tp-btn) {
  white-space: nowrap;
}

.tp-cases-export-format {
  width: 120px;
  flex: 0 0 120px;
  min-height: 40px;
}

:deep(.tp-toolbar__actions) {
  align-items: center;
}

@media (min-width: 1200px) {
  .tp-cases-panel-note {
    text-align: right;
  }

  :deep(.tp-toolbar__actions) {
    flex-wrap: nowrap;
  }
}
</style>
