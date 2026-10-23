<template>
  <section>
    <div v-if="pageNotice" class="tp-risk-block tp-mb-3" :class="pageNoticeClass">
      {{ pageNotice }}
    </div>
    <div class="tp-doc-page-actions tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-gap-2 tp-justify-end">
        <TpButton variant="ghost" @click="router.push('/documents/manage')">
          {{ t('documents.actions.backToDocuments') }}
        </TpButton>
        <TpButton variant="secondary" :loading="historyRequirementsLoading" @click="loadHistoryRequirements(1)">
          {{ t('common.actions.refresh') }}
        </TpButton>
        <TpButton
          variant="primary"
          :loading="generating"
          :disabled="generating || (!historyRequirements.length && !selectedRequirementIds.length)"
          @click="handleGenerateCases"
        >
          {{ generating ? t('documents.actions.generating') : t('documents.actions.generateCases') }}
        </TpButton>
        <TpButton variant="danger" :disabled="!selectedRequirementIds.length" @click="handleDeleteSelectedRequirements">
          {{ t('documents.actions.deleteRequirements') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-surface tp-p-3 tp-mt-3">
      <div class="tp-flex tp-gap-2 tp-align-center tp-flex-wrap tp-mb-3">
        <span v-if="selectedRequirementIds.length" class="tp-small" style="color: var(--tp-color-text-500)">
          {{ t('documents.history.selectedRequirementsCount', { count: selectedRequirementIds.length }) }}
        </span>
        <input
          v-model.trim="filters.search"
          class="tp-input"
          :placeholder="t('documents.history.searchPlaceholder')"
          @keyup.enter="handleFilterChange"
          style="min-width: 220px;"
        />
        <select v-model="filters.sourceFile" class="tp-select" @change="handleFilterChange">
          <option value="">{{ t('documents.history.sourceAll') }}</option>
          <option v-for="source in historySourceOptions" :key="source" :value="source">{{ source }}</option>
        </select>
      </div>

      <BaseTable
        :columns="historyRequirementColumns"
        :data="historyRequirements"
        :loading="historyRequirementsLoading"
        :loading-title="t('documents.history.loading')"
        :empty-title="t('documents.history.empty')"
        :empty-message="historyRequirementsError"
        :selectable="true"
        :selected-keys="selectedRequirementIds"
        row-key="req_id"
        @update:selectedKeys="handleSelectionUpdate"
        @toggleAll="handleRequirementToggleAll"
      >
        <template #cell-type="{ row }">
          {{ resolveRequirementTypeLabel((row as DocumentRequirementRecord).type) }}
        </template>
        <template #cell-priority="{ row }">
          {{ resolvePriorityLabel((row as DocumentRequirementRecord).priority) }}
        </template>
        <template #cell-source="{ row }">
          <div class="tp-history-cell-source" :title="(row as DocumentRequirementRecord).source_file || '-'">
            {{ (row as DocumentRequirementRecord).source_file || '-' }}
          </div>
        </template>
        <template #cell-actions="{ row }">
          <TpButton variant="danger" size="sm" @click="handleDeleteSingleRequirement((row as DocumentRequirementRecord).req_id)">
            {{ t('common.actions.delete') }}
          </TpButton>
        </template>
      </BaseTable>
      <TpPager
        v-if="historyRequirementsPagination.pages > 1"
        class="tp-mt-3"
        :page="historyRequirementsPagination.page"
        :per-page="historyRequirementsPagination.per_page"
        :total="historyRequirementsPagination.total"
        :pages="historyRequirementsPagination.pages"
        :has-prev="Boolean(historyRequirementsPagination.has_prev)"
        :has-next="Boolean(historyRequirementsPagination.has_next)"
        :previous-text="t('common.actions.previous')"
        :next-text="t('common.actions.next')"
        @change="changePage"
      />
    </div>

    <ConfirmDialog
      v-model="deleteConfirmVisible"
      :title="confirmDialogTitle"
      :message="confirmDialogMessage"
      :confirm-text="confirmDialogButtonText"
      :cancel-text="t('common.actions.cancel')"
      :confirm-variant="confirmDialogVariant"
      @confirm="runDeleteConfirmAction"
      @cancel="clearConfirmDialog"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import {
  deleteRequirement,
  generateCasesFromAnalysis,
  getDocumentRequirements,
  type DocumentRequirementRecord
} from '@/api/documents';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const filters = reactive({
  search: '',
  sourceFile: ''
});
const historyRequirements = ref<DocumentRequirementRecord[]>([]);
const historyRequirementsLoading = ref(false);
const generating = ref(false);
const pageNotice = ref('');
const pageNoticeTone = ref<'success' | 'warning' | 'danger'>('success');
const pageNoticeClass = computed(() => ({
  'tp-risk-block--success': pageNoticeTone.value === 'success',
  'tp-risk-block--warning': pageNoticeTone.value === 'warning',
  'tp-risk-block--danger': pageNoticeTone.value === 'danger'
}));
const historyRequirementsError = ref('');
const selectedRequirementIds = ref<Array<string | number>>([]);
const selectedRequirementMap = ref<Record<string, DocumentRequirementRecord>>({});
const historyRequirementsPagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});
const deleteConfirmVisible = ref(false);
const deleteConfirmAction = ref<null | (() => Promise<void>)>(null);
const confirmDialogTitle = ref(t('documents.actions.deleteRequirements'));
const confirmDialogMessage = ref(t('documents.confirm.deleteRequirements'));
const confirmDialogButtonText = ref(t('common.actions.delete'));
const confirmDialogVariant = ref<'primary' | 'danger' | 'warning'>('danger');

const historyRequirementColumns = computed<BaseTableColumn[]>(() => [
  { key: 'req_id', label: t('documents.requirement.id'), width: '130px' },
  { key: 'title', label: t('documents.requirement.title') },
  { key: 'type', label: t('documents.requirement.type'), width: '120px' },
  { key: 'priority', label: t('documents.requirement.priority'), width: '110px' },
  { key: 'source', label: t('documents.history.source'), width: '220px' },
  { key: 'actions', label: t('documents.table.columns.actions'), width: '110px' }
]);

const historySourceOptions = computed(() => {
  const set = new Set<string>();
  for (const item of historyRequirements.value) {
    const source = String(item.source_file || '').trim();
    if (source) set.add(source);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
});

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

function handleSelectionUpdate(values: Array<string | number>) {
  selectedRequirementIds.value = values;
}

async function handleRequirementToggleAll(checked: boolean) {
  if (!checked) {
    selectedRequirementIds.value = [];
    return;
  }
  const allRequirements = await fetchAllFilteredRequirements();
  selectedRequirementIds.value = allRequirements.map((item) => String(item.req_id));
  const nextMap = { ...selectedRequirementMap.value };
  for (const item of allRequirements) {
    nextMap[String(item.req_id)] = item;
  }
  selectedRequirementMap.value = nextMap;
}

async function fetchAllFilteredRequirements() {
  const allRequirements: DocumentRequirementRecord[] = [];
  let page = 1;
  const perPage = 200;
  while (true) {
    const response = await getDocumentRequirements({
      page,
      per_page: perPage,
      source_file: filters.sourceFile || undefined,
      search: filters.search || undefined
    });
    allRequirements.push(...response.requirements);
    if (!response.pagination.has_next || page >= (response.pagination.pages || 1)) break;
    page += 1;
  }
  return allRequirements;
}

async function loadHistoryRequirements(page = historyRequirementsPagination.value.page || 1) {
  historyRequirementsLoading.value = true;
  historyRequirementsError.value = '';
  try {
    const response = await getDocumentRequirements({
      page,
      per_page: historyRequirementsPagination.value.per_page,
      source_file: filters.sourceFile || undefined,
      search: filters.search || undefined
    });
    historyRequirements.value = response.requirements;
    for (const item of response.requirements) {
      selectedRequirementMap.value[String(item.req_id)] = item;
    }
    historyRequirementsPagination.value = response.pagination;
  } catch (error) {
    historyRequirements.value = [];
    historyRequirementsError.value = error instanceof Error ? error.message : t('documents.message.loadAnalysisFailed');
  } finally {
    historyRequirementsLoading.value = false;
  }
}

async function handleFilterChange() {
  await loadHistoryRequirements(1);
}

async function changePage(page: number) {
  if (page < 1 || page > (historyRequirementsPagination.value.pages || 1)) return;
  await loadHistoryRequirements(page);
}

function handleDeleteSingleRequirement(reqId: string) {
  confirmDialogTitle.value = t('documents.actions.deleteRequirements');
  confirmDialogMessage.value = t('documents.confirm.deleteRequirements');
  confirmDialogButtonText.value = t('common.actions.delete');
  confirmDialogVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteRequirements([reqId]);
  };
  deleteConfirmVisible.value = true;
}

function handleDeleteSelectedRequirements() {
  if (!selectedRequirementIds.value.length) return;
  const reqIds = selectedRequirementIds.value.map((id) => String(id));
  confirmDialogTitle.value = t('documents.actions.deleteRequirements');
  confirmDialogMessage.value = t('documents.confirm.deleteRequirements');
  confirmDialogButtonText.value = t('common.actions.delete');
  confirmDialogVariant.value = 'danger';
  deleteConfirmAction.value = async () => {
    await deleteRequirements(reqIds);
  };
  deleteConfirmVisible.value = true;
}

async function deleteRequirements(reqIds: string[]) {
  await Promise.allSettled(reqIds.map((reqId) => deleteRequirement(reqId)));
  selectedRequirementIds.value = [];
  await loadHistoryRequirements(historyRequirementsPagination.value.page || 1);
}

async function runDeleteConfirmAction() {
  const action = deleteConfirmAction.value;
  deleteConfirmAction.value = null;
  if (action) await action();
}

async function handleGenerateCases() {
  const selectedSet = new Set(selectedRequirementIds.value.map((id) => String(id)));
  const requirementsToGenerate = selectedSet.size
    ? selectedRequirementIds.value
      .map((id) => selectedRequirementMap.value[String(id)])
      .filter((item): item is DocumentRequirementRecord => Boolean(item))
    : historyRequirements.value;

  if (!requirementsToGenerate.length) return;

  if (requirementsToGenerate.length > 1) {
    confirmDialogTitle.value = t('documents.confirm.batchGenerateTitle');
    confirmDialogMessage.value = t('documents.confirm.batchGenerateByRequirementsMessage', {
      count: requirementsToGenerate.length,
      reqCount: requirementsToGenerate.length,
      caseCount: requirementsToGenerate.length * 3,
      skippedCount: 0
    });
    confirmDialogButtonText.value = t('common.actions.confirm');
    confirmDialogVariant.value = 'warning';
    deleteConfirmAction.value = async () => {
      await executeGenerateCases(requirementsToGenerate);
    };
    deleteConfirmVisible.value = true;
    return;
  }

  await executeGenerateCases(requirementsToGenerate);
}

function clearConfirmDialog() {
  deleteConfirmAction.value = null;
}

async function executeGenerateCases(requirementsToGenerate: DocumentRequirementRecord[]) {
  generating.value = true;
  pageNotice.value = '';
  try {
    const response = await generateCasesFromAnalysis({
      requirements: requirementsToGenerate
    });
    const failedCount = Number(response.failed_count || 0);
    pageNoticeTone.value = failedCount > 0 ? 'warning' : 'success';
    pageNotice.value = response.message || t('documents.message.generateSuccess');
    await router.push({ name: 'cases-manage' });
  } catch (error) {
    pageNoticeTone.value = 'danger';
    pageNotice.value = error instanceof Error ? error.message : t('documents.message.generateFailed');
  } finally {
    generating.value = false;
  }
}

onMounted(async () => {
  const sourceFromQuery = typeof route.query.source === 'string' ? route.query.source.trim() : '';
  if (sourceFromQuery) {
    filters.sourceFile = sourceFromQuery;
  }
  await loadHistoryRequirements(1);
});
</script>

<style scoped>
.tp-doc-page-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.tp-history-cell-source {
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

