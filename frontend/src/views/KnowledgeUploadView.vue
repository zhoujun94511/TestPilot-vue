<template>
  <section :class="pageRootMarkedClass(pageMarkerKnowledgeUpload)">
    <PageNoticeBanner
      :notice="pageBanner"
      @close="clearPageBanner"
    />

    <KnowledgeVectorDisabledState v-if="vectorDisabled" />
    <PagePanel
      v-else
      :title="t('knowledge.upload.title')"
      :subtitle="t('knowledge.upload.dragHint')"
    >
      <template #actions>
        <TpTag v-if="selectedFiles.length" variant="neutral">
          {{ selectedFiles.length === 1 ? selectedFiles[0].name : t('knowledge.upload.filesSelected', { count: selectedFiles.length }) }}
        </TpTag>
      </template>

      <TpInput
        v-model="uploadForm.category"
        as="select"
        :class="uploadCategoryFieldClass"
        :label="t('knowledge.upload.category')"
        :placeholder="t('knowledge.upload.categoryPlaceholder')"
        :options="categoryOptions"
        :disabled="vectorDisabled"
      />

      <BaseUpload
        v-model="selectedFiles"
        :label="t('knowledge.upload.file')"
        :choose-text="t('common.actions.chooseFile')"
        :submit-text="t('knowledge.upload.submit')"
        :loading-text="t('knowledge.actions.uploading')"
        :hint="uploadFileHint"
        :empty-text="t('knowledge.upload.empty')"
        :clear-text="t('common.actions.cancel')"
        accept=".txt,.csv,.docx,.pdf,.json,.md"
        :multiple="true"
        :loading="uploadLoading"
        :disabled="vectorDisabled"
        @submit="handleUpload"
      />
      <div v-if="uploadLoading" class="mt-2">
        <div :class="uploadProgressLabelClass">
          {{ t('knowledge.upload.progress') }} {{ uploadProgress }}%
        </div>
        <div :class="uploadProgressTrackClass">
          <div :class="uploadProgressFillClass" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
      </div>

      <TpInput
        v-model="uploadForm.description"
        as="textarea"
        class="mt-4"
        :label="t('knowledge.upload.description')"
        :rows="4"
        :placeholder="t('knowledge.upload.descriptionPlaceholder')"
        :disabled="vectorDisabled"
      />
    </PagePanel>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import KnowledgeVectorDisabledState from '@/components/knowledge/KnowledgeVectorDisabledState.vue';
import BaseUpload from '@/components/common/BaseUpload.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { pageMarkerKnowledgeUpload, pageRootMarkedClass } from '@/lib/page-layout-ui';
import {
  uploadCategoryFieldClass,
  uploadProgressFillClass,
  uploadProgressLabelClass,
  uploadProgressTrackClass
} from '@/lib/upload-ui';
import { cn } from '@/lib/utils';
import { useKnowledgeVectorGate } from '@/composables/useKnowledgeVectorNotice';
import { usePageNotifier } from '@/composables/usePageNotifier';
import {
  getKnowledgeConfig,
  uploadKnowledge,
  type KnowledgeCategory,
  type KnowledgeConfig
} from '@/api/knowledge';
import { ApiError } from '@/api/http';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { formatBytes } from '@/lib/format';

type NoticeType = 'success' | 'danger' | 'warning' | 'info';

interface SelectOption {
  value: string;
  label: string;
}

const { t } = useI18n();
const router = useRouter();
const { vectorDisabled } = useKnowledgeVectorGate();
const {
  banner: pageBanner,
  clearBanner: clearPageBanner,
  showNotice: notifyShowNotice
} = usePageNotifier();

const selectedFiles = ref<File[]>([]);
const uploadLoading = ref(false);
const uploadProgress = ref(0);

const uploadForm = reactive({
  category: 'test_cases' as KnowledgeCategory | string,
  description: ''
});

const serverConfig = ref<KnowledgeConfig | null>(null);

const uploadFileHint = computed(() => {
  const base = t('knowledge.upload.fileHint');
  const cfg = serverConfig.value;
  if (!cfg?.max_file_size && !(cfg?.allowed_extensions?.length)) return base;
  const types = (cfg.allowed_extensions || []).map((item) => item.toUpperCase()).join(' / ') || '-';
  return `${base} · ${t('knowledge.upload.serverHint', { size: formatBytes(cfg.max_file_size, { zero: '-' }), types })}`;
});

const categoryOptions = computed<SelectOption[]>(() => [
  { value: 'test_cases', label: t('knowledge.category.test_cases') },
  { value: 'requirements', label: t('knowledge.category.requirements') },
  { value: 'business_rules', label: t('knowledge.category.business_rules') },
  { value: 'best_practices', label: t('knowledge.category.best_practices') },
  { value: 'templates', label: t('knowledge.category.templates') },
  { value: 'other', label: t('knowledge.category.other') }
]);

function showNotice(type: NoticeType, message: string, details?: string[]) {
  notifyShowNotice(type, message, details?.length ? { details } : undefined);
}

function extractBatchFailureDetails(response: Record<string, unknown>) {
  const results = Array.isArray(response.results) ? response.results : [];
  const failedItems = results.filter((item) => {
    if (!item || typeof item !== 'object') return false;
    const row = item as Record<string, unknown>;
    return row.success === false || Number(row.status_code) >= 400;
  }) as Record<string, unknown>[];
  if (!failedItems.length) return [];
  return failedItems.map((item) => {
    const filename = String(item.filename || item.file_name || 'unknown');
    const reason = String(item.message || item.error || t('knowledge.message.uploadFailed'));
    return `${filename}: ${reason}`;
  });
}

async function handleUpload(fileOrFiles: File | File[]) {
  if (vectorDisabled.value) return;
  const filesToUpload = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
  if (!filesToUpload.length) {
    showNotice('warning', t('knowledge.message.selectFileFirst'));
    return;
  }
  const oversize = filesToUpload.find((file) => file.size <= 0);
  if (oversize) {
    showNotice('warning', t('knowledge.message.validateFailed'));
    return;
  }

  uploadLoading.value = true;
  uploadProgress.value = 0;
  selectedFiles.value = filesToUpload;
  try {
    const formData = new FormData();
    for (const file of filesToUpload) {
      formData.append('files', file);
    }
    formData.append('category', uploadForm.category || 'other');
    if (uploadForm.description.trim()) {
      formData.append('description', uploadForm.description.trim());
    }

    const response = await uploadKnowledge(formData, {
      onUploadProgress: (percent) => {
        uploadProgress.value = percent;
      }
    });
    uploadProgress.value = 100;
    const summary = response.summary as Record<string, unknown> | undefined;
    const failedCount = Number(summary?.failed_count ?? 0);
    const successCount = Number(summary?.success_count ?? (response.success ? filesToUpload.length : 0));

    if (summary) {
      const failureDetails = extractBatchFailureDetails(response as Record<string, unknown>);
      showNotice(
        failedCount > 0 ? 'warning' : 'success',
        failedCount > 0
          ? `${t('knowledge.message.uploadPartialFailed')} (${successCount}/${filesToUpload.length})`
          : `${t('knowledge.message.uploadSuccess')} (${successCount}/${filesToUpload.length})`,
        failedCount > 0 ? failureDetails : undefined
      );
      if (successCount > 0) {
        await router.push('/knowledge/files');
      }
    } else {
      const isDuplicate = Boolean(response.file_info && (response.file_info as Record<string, unknown>).is_duplicate);
      showNotice(
        'success',
        isDuplicate ? t('knowledge.message.uploadDuplicate') : t('knowledge.message.uploadSuccess')
      );
      await router.push('/knowledge/files');
    }

    selectedFiles.value = [];
    uploadForm.category = 'test_cases';
    uploadForm.description = '';
  } catch (error) {
    showNotice('danger', getUserFacingErrorMessage(error, t('knowledge.message.uploadFailed')));
  } finally {
    uploadLoading.value = false;
    uploadProgress.value = 0;
  }
}

onMounted(async () => {
  try {
    serverConfig.value = await getKnowledgeConfig();
  } catch {
    serverConfig.value = null;
  }
});
</script>

