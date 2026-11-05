<template>
  <section :class="pageRootMarkedClass(pageMarkerDocumentsHistory)">
    <PageNoticeBanner
      :notice="pageBanner"
      @close="clearPageBanner"
    />

    <PagePanel
      :title="t('documents.tabs.history')"
      :subtitle="t('documents.toolbar.historyLead')"
    >
      <template #actions>
        <div :class="pageToolbarStripClass">
          <TpButton variant="ghost" size="sm" @click="router.push('/documents/manage')">
            {{ t('documents.actions.backToDocuments') }}
          </TpButton>
          <TpButton variant="ghost" size="sm" :loading="historyRefreshLoading" @click="handleHistoryRefresh">
            {{ t('common.actions.refresh') }}
          </TpButton>
          <TpButton
            variant="primary"
            size="sm"
            :loading="generating"
            :disabled="generating || (!historyRequirements.length && !selectedRequirementIds.length)"
            @click="handleGenerateCases"
          >
            {{ generating ? t('documents.actions.generating') : t('documents.actions.generateCases') }}
          </TpButton>
        </div>
      </template>

      <ToolbarBulkBar
        :count="selectedRequirementIds.length"
        :count-label="t('documents.history.selectedRequirementsCount', { count: selectedRequirementIds.length })"
        @clear="clearRequirementSelection"
      >
        <TpButton variant="danger" size="sm" :disabled="!selectedRequirementIds.length" @click="handleDeleteSelectedRequirements">
          {{ t('documents.actions.deleteRequirements') }}
        </TpButton>
      </ToolbarBulkBar>

      <TableToolbar>
        <template #filters>
          <TableFilterInput
            v-model="filters.search"
            :placeholder="t('documents.history.searchPlaceholder')"
            @keyup="(event) => { if (event.key === 'Enter') handleFilterChange(); }"
          />
          <TableFilterSelect
            v-model="filters.sourceFile"
            class="min-w-[180px]"
            @change="handleFilterChange"
          >
            <option value="">{{ t('documents.history.sourceAll') }}</option>
            <option v-for="source in historySourceOptions" :key="source" :value="source">{{ source }}</option>
          </TableFilterSelect>
          <TableFilterSelect
            v-model="filters.type"
            class="min-w-[140px]"
            :aria-label="t('documents.requirement.type')"
            @change="handleFilterChange"
          >
            <option value="">{{ t('documents.history.typeAll') }}</option>
            <option v-for="option in historyTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </TableFilterSelect>
          <TableFilterSelect
            v-model="filters.priority"
            class="min-w-[140px]"
            :aria-label="t('documents.requirement.priority')"
            @change="handleFilterChange"
          >
            <option value="">{{ t('documents.history.priorityAll') }}</option>
            <option v-for="option in historyPriorityOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </TableFilterSelect>
        </template>
      </TableToolbar>

      <BaseTable
        :columns="historyRequirementColumns"
        :data="historyRequirements"
        :loading="historyRequirementsLoading"
        keep-content-while-loading
        :loading-title="t('documents.history.loading')"
        :empty-title="t('documents.history.empty')"
        :empty-message="historyRequirementsError"
        :error-empty-title="t('common.status.error')"
        :retry-text="t('common.actions.retry')"
        :selectable="true"
        @retry="() => loadHistoryRequirements(historyRequirementsPagination.page || 1, 'initial')"
        :managed-select-all="true"
        :selected-keys="selectedRequirementIds"
        row-key="req_id"
        @update:selectedKeys="handleSelectionUpdate"
        @toggleAll="handleRequirementToggleAll"
      >
        <template #toolbar>
          <TableToolbar :title="t('documents.history.title')" :pagination="historyRequirementsPagination" />
        </template>
        <template #cell-type="{ row }">
          {{ formatRequirementTypeLabel((row as DocumentRequirementRecord).type, t) }}
        </template>
        <template #cell-priority="{ row }">
          {{ resolvePriorityLabel((row as DocumentRequirementRecord).priority) }}
        </template>
        <template #cell-source="{ row }">
          <div :class="historyCellSourceClass" :title="displaySourceFile((row as DocumentRequirementRecord).source_file)">
            {{ displaySourceFile((row as DocumentRequirementRecord).source_file) }}
          </div>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex flex-nowrap justify-end gap-2">
            <TpButton variant="primary" size="sm" @click="openRequirementEditor(row as DocumentRequirementRecord)">
              {{ t('common.actions.edit') }}
            </TpButton>
            <TpButton variant="danger" size="sm" @click="handleDeleteSingleRequirement((row as DocumentRequirementRecord).req_id)">
              {{ t('common.actions.delete') }}
            </TpButton>
          </div>
        </template>
        <template #footer>
          <ListTablePager :pagination="historyRequirementsPagination" @change="changePage" />
        </template>
      </BaseTable>
    </PagePanel>

    <RequirementEditDrawer
      :visible="requirementEditVisible"
      :record="editingRequirement"
      :type-options="historyTypeOptions"
      :priority-options="historyPriorityOptions"
      @close="closeRequirementEditor"
      @saved="handleRequirementSaved"
      @error="(message) => showNotice('danger', message, { title: t('common.status.error') })"
    />

    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :confirm-text="confirm.confirmText"
      :cancel-text="confirm.cancelText"
      :confirm-variant="confirm.variant"
      @confirm="confirm.handleConfirm"
      @cancel="confirm.handleCancel"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import RequirementEditDrawer from '@/components/documents/RequirementEditDrawer.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import ListTablePager from '@/components/common/ListTablePager.vue';
import { useConfirmAction } from '@/composables/useConfirmAction';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import { TableFilterInput, TableFilterSelect } from '@/components/common/table';
import { historyCellSourceClass } from '@/lib/documents-ui';
import {
  buildRequirementTypeSelectOptions,
  resolveRequirementTypeLabel as formatRequirementTypeLabel
} from '@/lib/requirement-type-ui';
import { useListPageChange } from '@/composables/useListPageChange';
import { usePaginatedList } from '@/composables/usePaginatedList';
import type { ListFetchMode } from '@/lib/list-fetch-mode';
import ToolbarBulkBar from '@/components/common/ToolbarBulkBar.vue';
import { pageToolbarStripClass } from '@/lib/page-chrome-ui';
import { pageMarkerDocumentsHistory, pageRootMarkedClass } from '@/lib/page-layout-ui';
import TpButton from '@/components/ui/base/TpButton.vue';
import { usePageNotifier } from '@/composables/usePageNotifier';
import {
  deleteRequirement,
  generateCasesFromAnalysis,
  getDocumentRequirements,
  type DocumentRequirementRecord
} from '@/api/documents';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { publicFileLabel } from '@/lib/public-file-label';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  showNotice
} = usePageNotifier();

const filters = reactive({
  search: '',
  sourceFile: '',
  type: '',
  priority: ''
});

interface SelectOption {
  value: string;
  label: string;
}

const historyTypeOptions = computed<SelectOption[]>(() => buildRequirementTypeSelectOptions(t));

const historyPriorityOptions = computed<SelectOption[]>(() => [
  { value: 'P0', label: 'P0' },
  { value: 'P1', label: 'P1' },
  { value: 'P2', label: 'P2' },
  { value: 'P3', label: 'P3' }
]);
const historyRequirements = ref<DocumentRequirementRecord[]>([]);
const historyRefreshLoading = ref(false);
const generating = ref(false);
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
const {
  listLoading: historyRequirementsLoading,
  listError: historyRequirementsError,
  loadPage: loadHistoryRequirementsPage
} = usePaginatedList(historyRequirements, {
  refreshLoading: historyRefreshLoading,
  pagination: historyRequirementsPagination
});
const confirm = useConfirmAction(t('common.actions.cancel'));

const historyRequirementColumns = computed<BaseTableColumn[]>(() => [
  { key: 'req_id', label: t('documents.requirement.id'), width: '130px' },
  { key: 'title', label: t('documents.requirement.title') },
  { key: 'type', label: t('documents.requirement.type'), width: '120px' },
  { key: 'priority', label: t('documents.requirement.priority'), width: '110px' },
  { key: 'source', label: t('documents.history.source'), width: '220px' },
  { key: 'actions', label: t('documents.table.columns.actions'), width: '180px', headerClass: 'text-end', cellClass: 'text-end' }
]);

const requirementEditVisible = ref(false);
const editingRequirement = ref<DocumentRequirementRecord | null>(null);

function openRequirementEditor(row: DocumentRequirementRecord) {
  editingRequirement.value = row;
  requirementEditVisible.value = true;
}

function closeRequirementEditor() {
  requirementEditVisible.value = false;
  editingRequirement.value = null;
}

async function handleRequirementSaved(updated: DocumentRequirementRecord) {
  closeRequirementEditor();
  showNotice('success', t('documents.requirement.updateSuccess'), { title: t('common.feedback.success') });
  const index = historyRequirements.value.findIndex((item) => item.req_id === updated.req_id);
  if (index >= 0) historyRequirements.value[index] = updated;
  selectedRequirementMap.value[String(updated.req_id)] = updated;
}

function displaySourceFile(value?: string | null) {
  const label = publicFileLabel(String(value || '').trim());
  return label || '-';
}

const historySourceOptions = computed(() => {
  const set = new Set<string>();
  for (const item of historyRequirements.value) {
    const source = displaySourceFile(item.source_file);
    if (source !== '-') set.add(source);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
});

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

function clearRequirementSelection() {
  selectedRequirementIds.value = [];
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
      search: filters.search || undefined,
      type: filters.type || undefined,
      priority: filters.priority || undefined
    });
    allRequirements.push(...response.requirements);
    if (!response.pagination.has_next || page >= (response.pagination.pages || 1)) break;
    page += 1;
  }
  return allRequirements;
}

async function loadHistoryRequirements(
  page = historyRequirementsPagination.value.page || 1,
  mode: ListFetchMode = 'page'
) {
  const result = await loadHistoryRequirementsPage(
    page,
    mode,
    () =>
      getDocumentRequirements({
        page,
        per_page: historyRequirementsPagination.value.per_page,
        source_file: filters.sourceFile || undefined,
        search: filters.search || undefined,
        type: filters.type || undefined,
        priority: filters.priority || undefined
      }).then((response) => ({ rows: response.requirements, pagination: response.pagination })),
    {
      resolveMessage: (error) => getUserFacingErrorMessage(error, t('documents.message.loadAnalysisFailed')),
      onClear: () => {
        historyRequirements.value = [];
      }
    }
  );
  if (!result) return;
  for (const item of result.rows) {
    selectedRequirementMap.value[String(item.req_id)] = item;
  }
}

function handleHistoryRefresh() {
  void loadHistoryRequirements(historyRequirementsPagination.value.page || 1, 'refresh');
}

async function handleFilterChange() {
  await loadHistoryRequirements(1, 'filter');
}

const { changePage } = useListPageChange(historyRequirementsPagination, (page, mode) =>
  loadHistoryRequirements(page, mode)
);

function handleDeleteSingleRequirement(reqId: string) {
  confirm.open({
    title: t('documents.actions.deleteRequirements'),
    message: t('documents.confirm.deleteRequirements'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteRequirements([reqId]);
    }
  });
}

function handleDeleteSelectedRequirements() {
  if (!selectedRequirementIds.value.length) return;
  const reqIds = selectedRequirementIds.value.map((id) => String(id));
  confirm.open({
    title: t('documents.actions.deleteRequirements'),
    message: t('documents.confirm.deleteRequirements'),
    confirmText: t('common.actions.delete'),
    variant: 'danger',
    onConfirm: async () => {
      await deleteRequirements(reqIds);
    }
  });
}

async function deleteRequirements(reqIds: string[]) {
  const results = await Promise.allSettled(reqIds.map((reqId) => deleteRequirement(reqId)));
  const successCount = results.filter((item) => item.status === 'fulfilled').length;
  const failedCount = reqIds.length - successCount;

  if (failedCount > 0) {
    showNotice('warning', t('documents.message.deleteRequirementsPartial', { success: successCount, failed: failedCount }));
  } else {
    showNotice('success', t('documents.message.deleteRequirementSuccess'));
  }

  selectedRequirementIds.value = [];
  await loadHistoryRequirements(historyRequirementsPagination.value.page || 1, 'page');
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
    confirm.open({
      title: t('documents.confirm.batchGenerateTitle'),
      message: t('documents.confirm.batchGenerateByRequirementsMessage', {
        count: requirementsToGenerate.length,
        reqCount: requirementsToGenerate.length,
        caseCount: requirementsToGenerate.length * 3,
        skippedCount: 0
      }),
      confirmText: t('common.actions.confirm'),
      variant: 'warning',
      onConfirm: async () => {
        await executeGenerateCases(requirementsToGenerate);
      }
    });
    return;
  }

  await executeGenerateCases(requirementsToGenerate);
}

async function executeGenerateCases(requirementsToGenerate: DocumentRequirementRecord[]) {
  generating.value = true;
  try {
    const response = await generateCasesFromAnalysis({
      requirements: requirementsToGenerate
    });
    const failedCount = Number(response.failed_count || 0);
    showNotice(
      failedCount > 0 ? 'warning' : 'success',
      response.message || t('documents.message.generateSuccess')
    );
    await router.push({ name: 'cases-manage' });
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('documents.message.generateFailed')));
  } finally {
    generating.value = false;
  }
}

onMounted(async () => {
  const sourceFromQuery = typeof route.query.source === 'string' ? route.query.source.trim() : '';
  if (sourceFromQuery) {
    filters.sourceFile = sourceFromQuery;
  }
  await loadHistoryRequirements(1, 'initial');
});
</script>

