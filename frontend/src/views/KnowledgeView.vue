<template>
  <section class="tp-container-fluid tp-py-3 tp-page tp-page-shell tp-knowledge-page">
    <div v-if="notice" class="tp-risk-block tp-mb-3" :class="noticeClass">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-3">
        <div class="tp-flex-grow-1">
          <div>{{ notice.message }}</div>
          <div v-if="notice.details?.length" class="tp-mt-2">
            <TpButton variant="ghost" size="sm" @click="noticeDetailsExpanded = !noticeDetailsExpanded">
              {{ noticeDetailsExpanded ? t('common.actions.collapse') : t('common.actions.expand') }}
            </TpButton>
            <ul v-if="noticeDetailsExpanded" class="tp-mb-0 tp-mt-2 tp-ps-3 tp-small">
              <li v-for="(detail, idx) in notice.details" :key="idx">{{ detail }}</li>
            </ul>
          </div>
        </div>
        <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="notice = null">
          {{ t('common.actions.close') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-surface tp-p-3 tp-mb-3">
      <div class="tp-flex tp-flex-wrap tp-gap-2 tp-justify-end">
        <TpButton variant="secondary" :loading="refreshing" @click="handleRefresh">
          {{ t('knowledge.actions.refresh') }}
        </TpButton>
        <TpButton variant="warning" :loading="rebuilding" @click="openConfirm('rebuild')">
          {{ rebuilding ? t('knowledge.actions.rebuilding') : t('knowledge.actions.rebuild') }}
        </TpButton>
        <TpButton variant="danger" :loading="deleteLoading" :disabled="deleteLoading || !selectedIds.length" @click="openConfirm('delete')">
          {{ deleteLoading ? t('knowledge.actions.deleting') : t('knowledge.actions.batchDelete') }}
        </TpButton>
        <TpButton v-if="previewVisible" variant="ghost" @click="clearPreview">
          {{ t('common.actions.close') }}{{ t('knowledge.preview.title') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-row tp-g-3 tp-mb-3">
      <div class="tp-col-12 tp-col-md-6 tp-col-xxl-3" v-for="card in statsCards" :key="card.key">
        <KnowledgeStatsCard :label="card.label" :value="card.value" :hint="card.hint" :icon="card.icon" />
      </div>
    </div>

    <div class="tp-row tp-g-3 tp-knowledge-layout">
      <div class="tp-col-12 tp-knowledge-main-col">
        <div class="tp-surface tp-p-3 tp-mb-3 tp-knowledge-filter-sticky">
          <div class="tp-flex tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
            <div>
              <div class="tp-card__title">{{ t('knowledge.filters.title') }}</div>
              <div class="tp-card__subtitle">{{ t('knowledge.result.title') }}</div>
            </div>
            <div class="tp-small" style="color: var(--tp-color-text-500)">{{ paginationText }}</div>
          </div>

          <form class="tp-row tp-g-3 tp-align-end" @submit.prevent="handleSearch">
            <div class="tp-col-12 tp-col-lg-5">
              <label class="tp-form-label">{{ t('knowledge.filters.keywordLabel') }}</label>
              <input
                v-model.trim="filters.keyword"
                class="tp-input"
                type="search"
                :placeholder="t('knowledge.filters.keywordPlaceholder')"
                @keyup.enter="handleSearch"
              />
            </div>

            <div class="tp-col-12 tp-col-lg-3">
              <label class="tp-form-label">{{ t('knowledge.filters.categoryLabel') }}</label>
              <select v-model="filters.category" class="tp-select">
                <option value="">{{ t('knowledge.filters.categoryAll') }}</option>
                <option v-for="option in categoryOptions" :key="option.value || 'all'" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="tp-col-12 tp-col-lg-2">
              <label class="tp-form-label">{{ t('knowledge.filters.statusLabel') }}</label>
              <select v-model="filters.status" class="tp-select">
                <option value="">{{ t('knowledge.filters.statusAll') }}</option>
                <option v-for="option in statusOptions" :key="option.value || 'all'" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="tp-col-12 tp-col-lg-2 tp-grid">
              <TpButton :loading="searchLoading || listLoading" :disabled="searchLoading || listLoading" @click="handleSearch">
                {{ t('knowledge.actions.search') }}
              </TpButton>
            </div>
          </form>
        </div>

        <div class="tp-knowledge-workspace">
          <div class="tp-surface tp-p-3 tp-knowledge-panel tp-knowledge-panel--files">
            <div class="tp-flex tp-justify-between tp-align-center tp-gap-2 tp-mb-3">
              <div>
                <div class="tp-card__title">{{ t('knowledge.table.title') }}</div>
                <div v-if="selectedIds.length" class="tp-small" style="color: var(--tp-color-text-500)">{{ selectedIds.length }} / {{ files.length }}</div>
              </div>
              <label class="tp-toggle">
                <input class="tp-check" type="checkbox" :checked="allVisibleSelected" :disabled="!files.length" @change="toggleSelectAll(($event.target as HTMLInputElement).checked)" />
                <span class="tp-small">{{ t('knowledge.table.selectAll') }}</span>
              </label>
            </div>

            <div class="tp-knowledge-panel__body">
              <BaseTable
                :columns="tableColumns"
                :data="files"
                :loading="listLoading"
                :loading-title="t('knowledge.table.loading')"
                :empty-title="t('knowledge.table.empty')"
                :empty-message="listError"
                :selectable="true"
                :selected-keys="selectedIds"
                row-key="id"
                @update:selectedKeys="handleSelectionUpdate"
              >
                <template #cell-name="{ row }">
                    <div class="tp-data-title">{{ resolveFileName(row as KnowledgeFileRecord) }}</div>
                  <div v-if="(row as KnowledgeFileRecord).description" class="tp-data-subtitle text-truncate" style="max-width: 24rem">
                    {{ (row as KnowledgeFileRecord).description }}
                  </div>
                </template>
                <template #cell-category="{ row }">
                  {{ resolveCategoryLabel((row as KnowledgeFileRecord).category) }}
                </template>
                <template #cell-type="{ row }">
                  {{ resolveFileType((row as KnowledgeFileRecord).file_type) }}
                </template>
                <template #cell-size="{ row }">
                  {{ formatBytes((row as KnowledgeFileRecord).file_size) }}
                </template>
                <template #cell-chunks="{ row }">
                  {{ (row as KnowledgeFileRecord).document_count ?? 0 }}
                </template>
                <template #cell-status="{ row }">
                  <TpTag :variant="statusTagVariant(row as KnowledgeFileRecord)">
                    {{ resolveStatusLabel(row as KnowledgeFileRecord) }}
                  </TpTag>
                </template>
                <template #cell-updatedAt="{ row }">
                  {{ formatDateTime((row as KnowledgeFileRecord).updated_time || (row as KnowledgeFileRecord).created_time) }}
                </template>
                <template #cell-actions="{ row }">
                  <div class="tp-text-end tp-flex tp-justify-end tp-gap-2">
                    <TpButton variant="secondary" size="sm" @click="openPreview(row as KnowledgeFileRecord)">
                      {{ t('knowledge.actions.preview') }}
                    </TpButton>
                    <TpButton variant="danger" size="sm" @click="openDeleteOne((row as KnowledgeFileRecord).id)">
                      {{ t('knowledge.actions.delete') }}
                    </TpButton>
                  </div>
                </template>
              </BaseTable>
            </div>
            <div class="tp-knowledge-panel__footer">
              <TpPager
                v-if="pagination.pages > 1"
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
        </div>
      </div>
    </div>

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
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import BaseTable, { type BaseTableColumn } from '@/components/common/BaseTable.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import KnowledgeStatsCard from '@/components/common/KnowledgeStatsCard.vue';
import PreviewDrawer from '@/components/common/PreviewDrawer.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useAppStore } from '@/stores';
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

interface NoticeState {
  type: NoticeType;
  message: string;
  details?: string[];
}

interface SelectOption {
  value: string;
  label: string;
}

const { t, locale } = useI18n();
const route = useRoute();
const appStore = useAppStore();

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

const notice = ref<NoticeState | null>(null);
const noticeDetailsExpanded = ref(false);
const listLoading = ref(false);
const statsLoading = ref(false);
const deleteLoading = ref(false);
const rebuilding = ref(false);
const searchLoading = ref(false);
const previewLoading = ref(false);
const previewVisible = ref(false);
const listError = ref('');
const statsError = ref('');
const previewError = ref('');
const refreshing = ref(false);
const selectedIds = ref<number[]>([]);
const previewFile = ref<(KnowledgeFileRecord & { preview?: string; preview_type?: string; preview_truncated?: boolean }) | null>(null);
const currentLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'));

const confirm = reactive({
  visible: false,
  kind: '' as '' | 'delete' | 'rebuild',
  title: '',
  message: '',
  confirmText: '',
  cancelText: t('common.actions.cancel'),
  variant: 'danger' as 'primary' | 'danger' | 'warning',
  onConfirm: null as null | (() => Promise<void> | void)
});

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
  { key: 'actions', label: t('knowledge.table.columns.actions'), headerClass: 'tp-text-end', cellClass: 'tp-text-end' }
]);

const hasSelection = computed(() => selectedIds.value.length > 0);
const allVisibleSelected = computed(() => files.value.length > 0 && files.value.every((file) => selectedIds.value.includes(file.id)));

const paginationText = computed(() => {
  if (!pagination.value.total) return '';
  const start = (pagination.value.page - 1) * pagination.value.per_page + 1;
  const end = Math.min(pagination.value.page * pagination.value.per_page, pagination.value.total);
  return `${start} - ${end} / ${pagination.value.total}`;
});

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
    hint: stats.value?.last_update ? `${t('knowledge.stats.lastUpdate')}: ${formatDateTime(stats.value.last_update)}` : undefined,
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

const noticeClass = computed(() => {
  const type = notice.value?.type || 'info';
  return {
    'tp-risk-block--info': type === 'info',
    'tp-risk-block--danger': type === 'danger',
    'tp-risk-block--warning': type === 'warning',
    'tp-risk-block--success': type === 'success'
  };
});

const pageBusy = computed(() => listLoading.value || statsLoading.value || deleteLoading.value || rebuilding.value);

watch(pageBusy, (next) => {
  appStore.setLoading(next);
}, { immediate: true });

function translateOrFallback(path: string, fallback: string) {
  const value = t(path) as string;
  return value === path ? fallback : value;
}

function showNotice(type: NoticeType, message: string, details?: string[]) {
  notice.value = { type, message, details };
  noticeDetailsExpanded.value = false;
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


function statusTagVariant(file: KnowledgeFileRecord) {
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

function resolveFileType(type?: string | null) {
  return type ? type.toUpperCase() : '-';
}

function formatBytes(bytes?: number | null) {
  const value = Number(bytes || 0);
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDateTime(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(currentLocale.value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function handleSelectionUpdate(values: Array<string | number>) {
  selectedIds.value = values.map((item) => Number(item)).filter((item) => !Number.isNaN(item));
}

function toggleSelectAll(checked: boolean) {
  selectedIds.value = checked ? files.value.map((item) => item.id) : [];
}

function openConfirm(kind: 'delete' | 'rebuild') {
  if (kind === 'delete' && !selectedIds.value.length) {
    showNotice('warning', t('knowledge.message.noSelection'));
    return;
  }

  confirm.kind = kind;
  confirm.title = kind === 'delete' ? t('knowledge.actions.batchDelete') : t('knowledge.actions.rebuild');
  confirm.message = kind === 'delete' ? t('knowledge.confirm.deleteSelected') : t('knowledge.confirm.rebuild');
  confirm.confirmText = kind === 'delete' ? t('common.actions.delete') : t('common.actions.confirm');
  confirm.variant = 'danger';
  confirm.visible = true;
  confirm.onConfirm = kind === 'delete' ? () => deleteByIds([...selectedIds.value]) : () => handleRebuild();
}

async function runConfirmedAction() {
  const action = confirm.onConfirm;
  confirm.onConfirm = null;
  if (action) await action();
}

async function loadStats() {
  statsLoading.value = true;
  statsError.value = '';
  try {
    stats.value = await getKnowledgeStats();
  } catch (error) {
    stats.value = null;
    statsError.value = error instanceof Error ? error.message : t('knowledge.message.statsFailed');
  } finally {
    statsLoading.value = false;
  }
}

async function loadFiles(page = filters.page) {
  listLoading.value = true;
  listError.value = '';
  try {
    const response = await listKnowledge({
      page,
      per_page: filters.per_page,
      search: filters.keyword || undefined,
      category: filters.category || undefined,
      status: filters.status || undefined
    });
    files.value = response.files;
    pagination.value = response.pagination;
    filters.page = response.pagination.page || page;
    selectedIds.value = selectedIds.value.filter((id) => response.files.some((file) => file.id === id));
    if (previewFile.value && !response.files.some((file) => file.id === previewFile.value?.id)) {
      clearPreview();
    }
  } catch (error) {
    files.value = [];
    pagination.value = { page, per_page: filters.per_page, total: 0, pages: 0, has_prev: false, has_next: false };
    listError.value = error instanceof Error ? error.message : t('knowledge.message.loadFailed');
  } finally {
    listLoading.value = false;
  }
}

async function handleSearch() {
  searchLoading.value = true;
  filters.page = 1;
  try {
    await loadFiles(1);
  } finally {
    searchLoading.value = false;
  }
}

async function handleRefresh() {
  refreshing.value = true;
  try {
    await Promise.all([loadFiles(filters.page), loadStats()]);
    if (listError.value || statsError.value) {
      showNotice('warning', t('common.status.error'));
    } else {
      showNotice('success', t('knowledge.message.refreshSuccess'));
    }
  } finally {
    refreshing.value = false;
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
    previewError.value = error instanceof Error ? error.message : t('knowledge.preview.failed');
  } finally {
    previewLoading.value = false;
  }
}

function clearPreview() {
  previewVisible.value = false;
  previewFile.value = null;
  previewError.value = '';
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
      showNotice('warning', `${t('knowledge.message.deleteSuccess')}: ${deletedCount}, ${failedCount}`);
    } else {
      showNotice('success', t('knowledge.message.deleteSuccess'));
    }
    if (previewFile.value && ids.includes(previewFile.value.id)) {
      clearPreview();
    }
    selectedIds.value = [];
    await Promise.all([loadFiles(filters.page), loadStats()]);
  } catch (error) {
    showNotice('danger', error instanceof ApiError ? error.message : t('knowledge.message.batchDeleteFailed'));
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
    await rebuildKnowledgeIndex({ force: false, clear_all: false });
    showNotice('success', t('knowledge.message.rebuildSuccess'));
    await Promise.all([loadFiles(filters.page), loadStats()]);
  } catch (error) {
    showNotice('danger', error instanceof ApiError ? error.message : t('knowledge.message.rebuildFailed'));
  } finally {
    rebuilding.value = false;
  }
}

async function changePage(page: number) {
  if (page < 1 || page > (pagination.value.pages || 1)) return;
  filters.page = page;
  await loadFiles(page);
}

onMounted(async () => {
  await Promise.all([loadFiles(filters.page), loadStats()]);
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

<style scoped>
.tp-knowledge-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.tp-knowledge-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-gutter: stable;
}

.tp-knowledge-panel__footer {
  min-height: 42px;
  margin-top: 8px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
}

.tp-knowledge-filter-sticky {
  position: sticky;
  top: 72px;
  z-index: 30;
}

.tp-knowledge-workspace {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr;
  width: 100%;
}

.tp-knowledge-main-col {
  min-width: 0;
}

.tp-knowledge-panel--files .tp-knowledge-panel__body {
  overflow: hidden;
}

.tp-knowledge-panel--files .tp-knowledge-panel__body :deep(> div) {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tp-knowledge-panel--files :deep(.tp-table-wrap) {
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-gutter: stable both-edges;
}

@media (min-width: 1200px) {
  .tp-knowledge-layout {
    align-items: stretch;
  }

  .tp-knowledge-layout > .tp-knowledge-main-col {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .tp-knowledge-layout > .tp-knowledge-main-col {
    min-height: 100%;
  }

  .tp-knowledge-main-col .tp-knowledge-workspace {
    grid-template-columns: minmax(0, 1fr);
    align-items: stretch;
    width: 100%;
  }
}

@media (max-width: 1199px) {
  .tp-knowledge-filter-sticky {
    top: 12px;
  }
}

.tp-knowledge-panel--files :deep(.tp-table-wrap)::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.tp-knowledge-panel--files :deep(.tp-table-wrap)::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--tp-border-default) 85%, transparent);
  border-radius: 999px;
}

.tp-knowledge-panel--files :deep(.tp-table-wrap)::-webkit-scrollbar-track {
  background: transparent;
}

@media (max-width: 1199px) {
  /* preview drawer responsive style is managed in PreviewDrawer */
}
</style>

