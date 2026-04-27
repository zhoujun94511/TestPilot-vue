<template>
  <section class="tp-knowledge-upload-page">
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

    <div class="tp-surface tp-p-3">
      <div class="tp-flex tp-justify-between tp-align-start tp-gap-2 tp-mb-3">
        <div>
          <div class="tp-card__title">{{ t('knowledge.upload.title') }}</div>
          <div class="tp-card__subtitle">{{ t('knowledge.upload.dragHint') }}</div>
          <div class="tp-upload-category tp-mt-2">
            <label class="tp-form-label tp-mb-1">{{ t('knowledge.upload.category') }}</label>
            <select v-model="uploadForm.category" class="tp-select">
              <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>
        <TpTag v-if="selectedFiles.length" variant="neutral">
          {{ selectedFiles.length === 1 ? selectedFiles[0].name : t('knowledge.upload.filesSelected', { count: selectedFiles.length }) }}
        </TpTag>
      </div>

      <BaseUpload
        v-model="selectedFiles"
        :label="t('knowledge.upload.file')"
        :choose-text="t('common.actions.chooseFile')"
        :submit-text="t('knowledge.upload.submit')"
        :loading-text="t('knowledge.actions.uploading')"
        :hint="t('knowledge.upload.fileHint')"
        :empty-text="t('knowledge.upload.empty')"
        :clear-text="t('common.actions.cancel')"
        accept=".txt,.csv,.docx,.pdf,.json,.md"
        :multiple="true"
        :loading="uploadLoading"
        @submit="handleUpload"
      />
      <div v-if="uploadLoading" class="tp-upload-progress tp-mt-2">
        <div class="tp-upload-progress__label">
          {{ t('knowledge.upload.progress') }} {{ uploadProgress }}%
        </div>
        <div class="tp-upload-progress__bar">
          <div class="tp-upload-progress__bar-inner" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
      </div>

      <div class="tp-row tp-g-3 tp-mt-1">
        <div class="tp-col-12">
          <label class="tp-form-label">{{ t('knowledge.upload.description') }}</label>
          <textarea
            v-model.trim="uploadForm.description"
            class="tp-textarea"
            rows="4"
            :placeholder="t('knowledge.upload.descriptionPlaceholder')"
          ></textarea>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import BaseUpload from '@/components/common/BaseUpload.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  uploadKnowledge,
  type KnowledgeCategory
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

const { t } = useI18n();
const router = useRouter();
const selectedFiles = ref<File[]>([]);
const uploadLoading = ref(false);
const uploadProgress = ref(0);
const notice = ref<NoticeState | null>(null);
const noticeDetailsExpanded = ref(false);

const uploadForm = reactive({
  category: 'test_cases' as KnowledgeCategory | string,
  description: ''
});

const categoryOptions = computed<SelectOption[]>(() => [
  { value: 'test_cases', label: t('knowledge.category.test_cases') },
  { value: 'requirements', label: t('knowledge.category.requirements') },
  { value: 'business_rules', label: t('knowledge.category.business_rules') },
  { value: 'best_practices', label: t('knowledge.category.best_practices') },
  { value: 'templates', label: t('knowledge.category.templates') },
  { value: 'other', label: t('knowledge.category.other') }
]);

const noticeClass = computed(() => {
  const type = notice.value?.type || 'info';
  return {
    'tp-risk-block--info': type === 'info',
    'tp-risk-block--danger': type === 'danger',
    'tp-risk-block--warning': type === 'warning',
    'tp-risk-block--success': type === 'success'
  };
});

function showNotice(type: NoticeType, message: string, details?: string[]) {
  notice.value = { type, message, details };
  noticeDetailsExpanded.value = false;
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
  const filesToUpload = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
  if (!filesToUpload.length) {
    showNotice('warning', t('knowledge.message.selectFileFirst'));
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
      showNotice('success', isDuplicate ? t('knowledge.message.uploadDuplicate') : t('knowledge.message.uploadSuccess'));
      await router.push('/knowledge/files');
    }

    selectedFiles.value = [];
    uploadForm.category = 'test_cases';
    uploadForm.description = '';
  } catch (error) {
    showNotice('danger', error instanceof ApiError ? error.message : t('knowledge.message.uploadFailed'));
  } finally {
    uploadLoading.value = false;
    uploadProgress.value = 0;
  }
}
</script>

<style scoped>
.tp-upload-progress__label {
  font-size: 12px;
  color: var(--tp-color-text-500);
  margin-bottom: 6px;
}

.tp-upload-progress__bar {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: var(--tp-bg-subtle);
  overflow: hidden;
}

.tp-upload-progress__bar-inner {
  height: 100%;
  background: var(--tp-color-primary-500);
  transition: width 0.2s ease;
}

.tp-upload-category {
  max-width: 280px;
}
</style>
