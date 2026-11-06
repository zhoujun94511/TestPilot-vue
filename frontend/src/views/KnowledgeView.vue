<template>
  <section :class="pageRootMarkedClass(pageMarkerKnowledge)">
    <PageNoticeBanner :notice="pageBanner" @close="clearPageBanner" />

    <div :class="knowledgeLayoutClass">
      <div :class="[colSpan12, knowledgeMainColClass]">
        <PagePanel
          :class="cn(knowledgeFilesPanelClass, 'min-h-0 flex-1')"
          :padded="false"
          :title="t('knowledge.tabs.files')"
        >
          <template #actions>
            <div :class="pageToolbarStripClass">
              <TpButton variant="ghost" size="sm" :loading="refreshing" @click="handleRefresh">
                {{ t('common.actions.refresh') }}
              </TpButton>
              <ToolbarOverflowMenu v-if="canRebuild || previewVisible">
                <DropdownMenuItem
                  v-if="canRebuild"
                  :disabled="vectorDisabled || rebuilding"
                  @select="openConfirm('rebuild')"
                >
                  {{ rebuilding ? t('knowledge.actions.rebuilding') : t('knowledge.actions.rebuild') }}
                </DropdownMenuItem>
                <DropdownMenuItem v-if="previewVisible" @select="clearPreview">
                  {{ t('knowledge.actions.closeResults') }}
                </DropdownMenuItem>
              </ToolbarOverflowMenu>
            </div>
          </template>

          <div class="px-[var(--tp-space-4)]">
            <ToolbarBulkBar
              :count="selectedIds.length"
              :select-all-count="knowledgeSelectAllCount"
              @clear="clearKnowledgeSelection"
              @select-all="selectAllMatchingKnowledge"
            >
              <TpButton
                variant="danger"
                size="sm"
                :loading="deleteLoading"
                :disabled="vectorDisabled || !selectedIds.length"
                :aria-label="deleteLoading ? t('knowledge.actions.deleting') : undefined"
                @click="openConfirm('delete')"
              >
                {{ t('knowledge.actions.batchDelete') }}
              </TpButton>
            </ToolbarBulkBar>
          </div>

          <div class="min-w-0 px-[var(--tp-space-4)] pb-0 pt-[var(--tp-space-4)]">
            <PagePanel :title="t('knowledge.stats.title')" :padded="true" flat>
              <div :class="grid12Class">
                <div v-for="card in statsCards" :key="card.key" :class="colSpan12Md6Min1400_3">
                  <KnowledgeStatsCard :label="card.label" :value="card.value" :hint="card.hint" :icon="card.icon" />
                </div>
              </div>
            </PagePanel>
          </div>

          <div
            v-if="!vectorDisabled"
            :class="cn(pageSectionDivideClass, knowledgeFilterStickyClass, 'z-30 bg-[var(--tp-bg-surface)] px-[var(--tp-space-4)]')"
          >
            <TableToolbar :title="t('knowledge.filters.title')">
              <template #filters>
                <TableFilterForm @submit="handleSearch">
                  <TableFilterInput
                    v-model="filters.keyword"
                    :placeholder="t('knowledge.filters.keywordPlaceholder')"
                    :aria-label="t('knowledge.filters.keywordLabel')"
                  />
                  <TableFilterSelect
                    v-model="filters.category"
                    class="min-w-[140px]"
                    :aria-label="t('knowledge.filters.categoryLabel')"
                  >
                    <option value="">{{ t('knowledge.filters.categoryAll') }}</option>
                    <option v-for="option in categoryOptions" :key="option.value || 'all'" :value="option.value">
                      {{ option.label }}
                    </option>
                  </TableFilterSelect>
                  <TableFilterSelect v-model="filters.status" :aria-label="t('knowledge.filters.statusLabel')">
                    <option value="">{{ t('knowledge.filters.statusAll') }}</option>
                    <option v-for="option in statusOptions" :key="option.value || 'all'" :value="option.value">
                      {{ option.label }}
                    </option>
                  </TableFilterSelect>
                  <TpButton :loading="searchLoading" type="submit">
                    {{ t('knowledge.filters.apply') }}
                  </TpButton>
                </TableFilterForm>
              </template>
            </TableToolbar>
          </div>

          <div :class="cn(pageSectionDivideClass, 'flex min-h-0 flex-1 flex-col')">
          <KnowledgeVectorDisabledState v-if="vectorDisabled" class="mx-4 mb-4" />
          <template v-else>
            <div :class="knowledgeFilesPanelBodyClass">
              <BaseTable
                :columns="tableColumns"
                :data="files"
                :loading="listLoading"
                keep-content-while-loading
                :loading-title="t('knowledge.table.loading')"
                :empty-title="t('knowledge.table.empty')"
                :empty-message="listError"
                :error-empty-title="t('common.status.error')"
                :retry-text="t('common.actions.retry')"
                :selectable="true"
                @retry="() => loadFiles(filters.page, 'initial')"
                :selected-keys="selectedIds"
                row-key="id"
                @update:selectedKeys="handleSelectionUpdate"
              >
                <template #toolbar>
                  <TableToolbar :title="t('knowledge.table.title')" :pagination="pagination">
                    <template #actions>
                      <div :class="[captionTextClass, 'text-[var(--tp-color-text-500)]']">
                        {{ t('common.toolbar.selectedCount', { count: selectedIds.length }) }} / {{ pagination.total }}
                      </div>
                    </template>
                  </TableToolbar>
                </template>
                <template #cell-name="{ row }">
                  <div :class="dataTitleClass">{{ resolveFileName(row as KnowledgeFileRecord) }}</div>
                  <TpTruncateText
                    v-if="(row as KnowledgeFileRecord).description"
                    :text="(row as KnowledgeFileRecord).description || ''"
                    :class="[dataSubtitleDenseClass, 'max-w-96']"
                  />
                </template>
                <template #cell-category="{ row }">
                  {{ resolveCategoryLabel((row as KnowledgeFileRecord).category) }}
                </template>
                <template #cell-type="{ row }">
                  {{ resolveFileType((row as KnowledgeFileRecord).file_type) }}
                </template>
                <template #cell-size="{ row }">
                  {{ formatBytes((row as KnowledgeFileRecord).file_size, { zero: '-' }) }}
                </template>
                <template #cell-chunks="{ row }">
                  {{ (row as KnowledgeFileRecord).document_count ?? 0 }}
                </template>
                <template #cell-status="{ row }">
                  <TpTag :variant="knowledgeFileStatusTagVariant(row as KnowledgeFileRecord)">
                    {{ resolveStatusLabel(row as KnowledgeFileRecord) }}
                  </TpTag>
                </template>
                <template #cell-updatedAt="{ row }">
                  {{ formatDateTimeLocalized((row as KnowledgeFileRecord).updated_time || (row as KnowledgeFileRecord).created_time) }}
                </template>
                <template #cell-actions="{ row }">
                  <div :class="flexWrapEndGap2Class">
                    <TpButton variant="primary" size="sm" @click="openMetaEditor(row as KnowledgeFileRecord)">
                      {{ t('common.actions.edit') }}
                    </TpButton>
                    <TpButton variant="secondary" size="sm" @click="openPreview(row as KnowledgeFileRecord)">
                      {{ t('knowledge.actions.preview') }}
                    </TpButton>
                    <TpButton variant="danger" size="sm" @click="openDeleteOne((row as KnowledgeFileRecord).id)">
                      {{ t('knowledge.actions.delete') }}
                    </TpButton>
                  </div>
                </template>
                <template #footer>
                  <ListTablePager :pagination="pagination" @change="changePage" />
                </template>
              </BaseTable>
            </div>
          </template>
          </div>
        </PagePanel>
      </div>
    </div>

    <KnowledgeMetaEditDrawer
      :visible="metaEditVisible"
      :record="metaEditRecord"
      :category-options="categoryOptions"
      @close="closeMetaEditor"
      @saved="handleMetaSaved"
      @error="(message) => showNotice('danger', message, { title: t('common.status.error') })"
    />

    <PreviewDrawer
      :visible="previewVisible"
      :title="t('knowledge.preview.title')"
      :subtitle="previewFile?.file_name || '-'"
      :meta-line="previewMetaLine"
      :content="previewFile?.preview || t('knowledge.preview.noContent')"
      :loading="previewLoading"
      :error="previewError"
      :loading-title="t('knowledge.preview.loading')"
      :empty-title="t('knowledge.preview.empty')"
      :error-title="t('common.status.error')"
      :close-text="t('common.actions.close')"
      :copy-text="t('common.actions.copy')"
      :copied-text="t('common.actions.copied')"
      :copyable="true"
      @copied="handlePreviewCopied"
      @copyFailed="handlePreviewCopyFailed"
      @close="clearPreview"
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import KnowledgeMetaEditDrawer from '@/components/knowledge/KnowledgeMetaEditDrawer.vue';
import KnowledgeVectorDisabledState from '@/components/knowledge/KnowledgeVectorDisabledState.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import ListTablePager from '@/components/common/ListTablePager.vue';
import { useConfirmAction } from '@/composables/useConfirmAction';
import { useListPageChange } from '@/composables/useListPageChange';
import { emptyListPagination, usePaginatedList } from '@/composables/usePaginatedList';
import { formatBytes, formatDateTime } from '@/lib/format';
import { knowledgeFileStatusTagVariant } from '@/lib/enum-tag-ui';
import KnowledgeStatsCard from '@/components/common/KnowledgeStatsCard.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import PreviewDrawer from '@/components/common/PreviewDrawer.vue';
import TableToolbar from '@/components/common/TableToolbar.vue';
import { TableFilterForm, TableFilterInput, TableFilterSelect } from '@/components/common/table';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpTruncateText from '@/components/ui/base/TpTruncateText.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { refreshAppFeatureFlags } from '@/composables/useFeatureFlags';
import { useKnowledgeVectorGate } from '@/composables/useKnowledgeVectorNotice';
import { usePageNotifier, type PageNoticeExtras } from '@/composables/usePageNotifier';
import ToolbarBulkBar from '@/components/common/ToolbarBulkBar.vue';
import ToolbarOverflowMenu from '@/components/common/ToolbarOverflowMenu.vue';
import { DropdownMenuItem } from '@/components/ui/dropdown-menu';
import type { ListFetchMode } from '@/lib/list-fetch-mode';
import { flexWrapEndGap2Class, pageToolbarStripClass } from '@/lib/page-chrome-ui';
import {
  colSpan12,
  colSpan12Md6Min1400_3,
  grid12Class,
  pageMarkerKnowledge,
  pageRootMarkedClass,
  pageSectionDivideClass
} from '@/lib/page-layout-ui';
import {
  knowledgeFilesPanelBodyClass,
  knowledgeFilesPanelClass,
  knowledgeFilterStickyClass,
  knowledgeLayoutClass,
  knowledgeMainColClass
} from '@/lib/knowledge-ui';
import {
  captionTextClass,
  dataSubtitleDenseClass,
  dataTitleClass
} from '@/lib/page-typography';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { tableCellAlignEndClass } from '@/lib/table-ui';
import { useAppStore, useAuthStore } from '@/stores';
import {
  batchDeleteKnowledge,
  getKnowledgeFileDetail,
  getKnowledgeStats,
  listKnowledge,
  rebuildKnowledgeIndex,
  type KnowledgeFileRecord,
  type KnowledgePagination,
  type KnowledgeStats
} from '@/api/knowledge';
import { ApiError } from '@/api/http';

type NoticeType = 'success' | 'danger' | 'warning' | 'info';

interface SelectOption {
  value: string;
  label: string;
}

const { t, locale } = useI18n();
const route = useRoute();
const appStore = useAppStore();
const authStore = useAuthStore();
const canRebuild = computed(() => authStore.canManageKnowledgeIndex());
const { vectorDisabled } = useKnowledgeVectorGate();
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  showNotice: notifyShowNotice
} = usePageNotifier();

const files = ref<KnowledgeFileRecord[]>([]);
const stats = ref<KnowledgeStats | null>(null);
const pagination = ref<KnowledgePagination>({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

const filters = reactive({
  keyword: '',
  category: '',
  status: '',
  page: 1,
  per_page: 10
});

const statsLoading = ref(false);
const deleteLoading = ref(false);
const rebuilding = ref(false);
const searchLoading = ref(false);
const previewLoading = ref(false);
const previewVisible = ref(false);
const metaEditVisible = ref(false);
const metaEditRecord = ref<KnowledgeFileRecord | null>(null);
const statsError = ref('');
const previewError = ref('');
const refreshing = ref(false);
const { listLoading, listError, loadPage: loadKnowledgePage } = usePaginatedList(files, {
  refreshLoading: refreshing,
  pagination
});
const selectedIds = ref<number[]>([]);
const previewFile = ref<(KnowledgeFileRecord & { preview?: string; preview_type?: string; preview_truncated?: boolean }) | null>(null);
const currentLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'));

const confirmDialog = useConfirmAction(t('common.actions.cancel'));

const categoryOptions = computed<SelectOption[]>(() => [
  { value: 'test_cases', label: t('knowledge.category.test_cases') },
  { value: 'requirements', label: t('knowledge.category.requirements') },
  { value: 'business_rules', label: t('knowledge.category.business_rules') },
  { value: 'best_practices', label: t('knowledge.category.best_practices') },
  { value: 'templates', label: t('knowledge.category.templates') },
  { value: 'other', label: t('knowledge.category.other') }
]);

const statusOptions = computed<SelectOption[]>(() => [
  { value: 'active', label: t('knowledge.status.active') },
  { value: 'processing', label: t('knowledge.status.processing') },
  { value: 'archived', label: t('knowledge.status.archived') },
  { value: 'failed', label: t('knowledge.status.failed') }
]);

const tableColumns = computed<BaseTableColumn[]>(() => [
  { key: 'name', label: t('knowledge.table.columns.name') },
  { key: 'category', label: t('knowledge.table.columns.category') },
  { key: 'type', label: t('knowledge.table.columns.type') },
  { key: 'size', label: t('knowledge.table.columns.size') },
  { key: 'chunks', label: t('knowledge.table.columns.chunks') },
  { key: 'status', label: t('knowledge.table.columns.status') },
  { key: 'updatedAt', label: t('knowledge.table.columns.updatedAt') },
  {
    key: 'actions',
    label: t('knowledge.table.columns.actions'),
    headerClass: tableCellAlignEndClass,
    cellClass: tableCellAlignEndClass
  }
]);

const hasSelection = computed(() => selectedIds.value.length > 0);

const statsCards = computed(() => [
  { key: 'total-files', label: t('knowledge.stats.totalFiles'), value: stats.value?.total_files ?? 0, hint: statsError.value || undefined, icon: 'KB' },
  {
    key: 'total-chunks',
    label: t('knowledge.stats.totalChunks'),
    value: stats.value?.total_chunks ?? 0,
    hint: stats.value ? `${t('knowledge.stats.indexStatus')}: ${stats.value.total_chunks > 0 ? t('knowledge.stats.indexReady') : t('knowledge.stats.indexEmpty')}` : undefined,
    icon: 'CH'
  },
  {
    key: 'storage-size',
    label: t('knowledge.stats.storageSize'),
    value: formatBytes(stats.value?.storage_size ?? 0),
    hint: stats.value?.last_update ? `${t('knowledge.stats.lastUpdate')}: ${formatDateTimeLocalized(stats.value.last_update)}` : undefined,
    icon: 'ST'
  },
  {
    key: 'vector-store',
    label: t('knowledge.stats.vectorEnabled'),
    value: appStore.featureFlags.enableVectorStore ? t('knowledge.stats.vectorOn') : t('knowledge.stats.vectorOff'),
    hint: stats.value ? `${t('knowledge.stats.categoryDistribution')}: ${Object.keys(stats.value.category_distribution || {}).length}` : undefined,
    icon: 'VS'
  }
]);

const previewMetaLine = computed(() => {
  if (!previewFile.value) return '';
  const type = String(previewFile.value.preview_type || previewFile.value.file_type || '-').toUpperCase();
  const size = formatBytes(previewFile.value.file_size || 0);
  const base = `${t('knowledge.preview.metaType', { type })} · ${t('knowledge.preview.metaSize', { size })}`;
  return previewFile.value.preview_truncated ? `${base} · ${t('knowledge.preview.truncated')}` : base;
});

const pageBusy = computed(() => listLoading.value || statsLoading.value || deleteLoading.value || rebuilding.value);

watch(pageBusy, (next) => {
  appStore.setLoading(next);
}, { immediate: true });

function translateOrFallback(path: string, fallback: string) {
  const value = t(path) as string;
  return value === path ? fallback : value;
}

function showNotice(type: NoticeType, message: string, extras?: PageNoticeExtras) {
  notifyShowNotice(type, message, extras);
}

function humanize(value?: string | null) {
  if (!value) return '-';
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/\b\w/g, (part) => part.toUpperCase());
}

function resolveCategoryLabel(category?: string | null) {
  if (!category) return '-';
  return translateOrFallback(`knowledge.category.${category}`, humanize(category));
}

function resolveFileName(file: KnowledgeFileRecord) {
  return file.file_name || file.filename || `#${file.id}`;
}

function resolveStatusLabel(file: KnowledgeFileRecord) {
  if (file.is_duplicate) return t('knowledge.status.duplicate');
  const status = file.status || 'active';
  return translateOrFallback(`knowledge.status.${status}`, humanize(status));
}


function resolveFileType(type?: string | null) {
  return type ? type.toUpperCase() : '-';
}

function formatDateTimeLocalized(value?: string | null) {
  return formatDateTime(value, currentLocale.value);
}

function handleSelectionUpdate(values: Array<string | number>) {
  selectedIds.value = values.map((item) => Number(item)).filter((item) => !Number.isNaN(item));
}

function clearKnowledgeSelection() {
  selectedIds.value = [];
}

const knowledgeSelectAllCount = computed(() => {
  const total = Number(pagination.value.total || 0);
  const pageSelected = files.value.length > 0 && files.value.every((file) => selectedIds.value.includes(file.id));
  return pageSelected && total > selectedIds.value.length ? total : 0;
});

async function selectAllMatchingKnowledge() {
  const ids: number[] = [];
  let page = 1;
  while (page <= 100) {
    const response = await listKnowledge({
      page,
      per_page: 200,
      search: filters.keyword || undefined,
      category: filters.category || undefined,
      status: filters.status || undefined
    });
    ids.push(...response.files.map((file) => file.id).filter((id) => Number.isFinite(id)));
    if (!response.pagination.has_next || page >= (response.pagination.pages || 1)) break;
    page += 1;
  }
  selectedIds.value = ids;
}

function openConfirm(kind: 'delete' | 'rebuild') {
  if (vectorDisabled.value) return;
  if (kind === 'delete' && !selectedIds.value.length) {
    showNotice('warning', t('knowledge.message.noSelection'));
    return;
  }

  confirmDialog.open({
    title: kind === 'delete' ? t('knowledge.actions.batchDelete') : t('knowledge.actions.rebuild'),
    message: kind === 'delete' ? t('knowledge.confirm.deleteSelected') : t('knowledge.confirm.rebuild'),
    confirmText: kind === 'delete' ? t('common.actions.delete') : t('common.actions.confirm'),
    variant: 'danger',
    onConfirm: async () => {
      if (kind === 'delete') {
        await deleteByIds([...selectedIds.value]);
      } else {
        await handleRebuild();
      }
    }
  });
}

async function loadStats() {
  if (vectorDisabled.value) {
    stats.value = null;
    statsError.value = '';
    return;
  }
  statsLoading.value = true;
  statsError.value = '';
  try {
    stats.value = await getKnowledgeStats();
  } catch (error) {
    stats.value = null;
    statsError.value = getUserFacingErrorMessage(error, t('knowledge.message.statsFailed'));
  } finally {
    statsLoading.value = false;
  }
}

async function loadFiles(page = filters.page, mode: ListFetchMode = 'page') {
  if (vectorDisabled.value) {
    files.value = [];
    listError.value = '';
    pagination.value = emptyListPagination(filters.per_page);
    return;
  }
  const result = await loadKnowledgePage(
    page,
    mode,
    () =>
      listKnowledge({
        page,
        per_page: filters.per_page,
        search: filters.keyword || undefined,
        category: filters.category || undefined,
        status: filters.status || undefined
      }).then((response) => ({ rows: response.files, pagination: response.pagination })),
    {
      resolveMessage: (error) => getUserFacingErrorMessage(error, t('knowledge.message.loadFailed')),
      onClear: () => {
        pagination.value = emptyListPagination(filters.per_page, page);
      }
    }
  );
  if (!result) return;
  filters.page = result.pagination.page || page;
  if (mode === 'filter') selectedIds.value = [];
  if (previewFile.value && !result.rows.some((file) => file.id === previewFile.value?.id)) {
    clearPreview();
  }
}

async function handleSearch() {
  filters.page = 1;
  selectedIds.value = [];
  const hasRows = files.value.length > 0;
  if (!hasRows) searchLoading.value = true;
  try {
    await loadFiles(1, hasRows ? 'page' : 'filter');
  } finally {
    searchLoading.value = false;
  }
}

async function handleRefresh() {
  try {
    await Promise.all([loadFiles(filters.page, 'refresh'), loadStats()]);
    if (listError.value || statsError.value) {
      showNotice('warning', t('common.status.error'));
    } else {
      showNotice('success', t('knowledge.message.refreshSuccess'));
    }
  } catch {
    showNotice('warning', t('common.status.error'));
  }
}

async function openPreview(file: KnowledgeFileRecord) {
  previewVisible.value = true;
  previewLoading.value = true;
  previewError.value = '';
  try {
    const detail = await getKnowledgeFileDetail(file.id);
    previewFile.value = detail;
  } catch (error) {
    previewFile.value = null;
    previewError.value = getUserFacingErrorMessage(error, t('knowledge.preview.failed'));
  } finally {
    previewLoading.value = false;
  }
}

function clearPreview() {
  previewVisible.value = false;
  previewFile.value = null;
  previewError.value = '';
}

function openMetaEditor(file: KnowledgeFileRecord) {
  metaEditRecord.value = file;
  metaEditVisible.value = true;
}

function closeMetaEditor() {
  metaEditVisible.value = false;
  metaEditRecord.value = null;
}

function handleMetaSaved(updated: KnowledgeFileRecord) {
  closeMetaEditor();
  showNotice('success', t('knowledge.edit.success'), { title: t('common.feedback.success') });
  const index = files.value.findIndex((item) => item.id === updated.id);
  if (index >= 0) {
    files.value[index] = { ...files.value[index], ...updated };
  }
}

function handlePreviewCopied() {
  showNotice('success', t('knowledge.message.previewCopySuccess'));
}

function handlePreviewCopyFailed() {
  showNotice('warning', t('knowledge.message.previewCopyFailed'));
}

async function deleteByIds(ids: number[]) {
  deleteLoading.value = true;
  try {
    const response = await batchDeleteKnowledge(ids);
    const deletedCount = Number(response.deleted_count ?? ids.length);
    const failedCount = Number(response.failed_count ?? 0);
    if (failedCount > 0) {
      const partial = `${t('knowledge.message.deleteSuccess')}: ${deletedCount}, ${failedCount}`;
      showNotice(
        deletedCount > 0 ? 'warning' : 'danger',
        deletedCount > 0 ? partial : t('knowledge.message.batchDeleteFailed')
      );
    } else {
      showNotice('success', t('knowledge.message.deleteSuccess'));
    }
    if (previewFile.value && ids.includes(previewFile.value.id)) {
      clearPreview();
    }
    selectedIds.value = [];
    await Promise.all([loadFiles(filters.page, 'refresh'), loadStats()]);
  } catch (error) {
    const fallback = ids.length > 1 ? t('knowledge.message.batchDeleteFailed') : t('knowledge.message.deleteFailed');
    showNotice('danger', getUserFacingErrorMessage(error, fallback));
  } finally {
    deleteLoading.value = false;
  }
}

function openDeleteOne(id: number) {
  selectedIds.value = [id];
  openConfirm('delete');
}

async function handleRebuild() {
  rebuilding.value = true;
  try {
    await rebuildKnowledgeIndex({ clear_all: false });
    showNotice('success', t('knowledge.message.rebuildSuccess'));
    await Promise.all([loadFiles(filters.page, 'refresh'), loadStats()]);
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('knowledge.message.rebuildFailed')));
  } finally {
    rebuilding.value = false;
  }
}

const { changePage } = useListPageChange(
  pagination,
  (page, mode) => loadFiles(page, mode),
  { onAcceptPage: (page) => { filters.page = page; } }
);

onBeforeUnmount(() => {
  appStore.setLoading(false);
});

onMounted(async () => {
  await refreshAppFeatureFlags();
  await Promise.all([loadFiles(filters.page, 'initial'), loadStats()]);
  const previewIdRaw = route.query.previewId;
  const previewId = typeof previewIdRaw === 'string' ? Number(previewIdRaw) : NaN;
  if (!Number.isNaN(previewId) && previewId > 0) {
    const matched = files.value.find((item) => item.id === previewId);
    if (matched) {
      await openPreview(matched);
    } else {
      try {
        const detail = await getKnowledgeFileDetail(previewId);
        previewFile.value = detail;
        previewVisible.value = true;
      } catch {
        // ignore route-driven preview failures
      }
    }
  }
});
</script>

