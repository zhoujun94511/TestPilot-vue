<template>
  <FormSideDrawer
    :open="visible"
    :title="t('cases.edit.title')"
    :subtitle="activeRecord ? resolveCaseId(activeRecord) : ''"
    :aria-label="t('cases.edit.title')"
    @close="emit('close')"
  >
    <BaseState v-if="loading" variant="loading" :title="t('cases.edit.loading')" />
    <BaseState v-else-if="loadError" variant="error" :title="t('common.status.error')" :message="loadError" />
    <BaseState v-else-if="!activeRecord" variant="empty" :title="t('cases.edit.noCase')" />
    <div v-else class="flex flex-col gap-4">
      <TpInput
        v-model="form.title"
        :label="t('cases.table.columns.title')"
        required
        :error="fieldErrors.title"
      />
      <TpInput v-model="form.description" as="textarea" :label="t('cases.edit.descriptionLabel')" :rows="3" />
      <TpInput v-model="form.precondition" as="textarea" :label="t('cases.edit.preconditionLabel')" :rows="3" />
      <div class="grid gap-4 md:grid-cols-2">
        <TpInput v-model="form.module" :label="t('cases.table.columns.module')" />
        <TpInput v-model="form.testMethod" :label="t('cases.table.columns.testMethod')" />
      </div>
      <TpInput
        v-model="form.stepsText"
        as="textarea"
        :label="t('cases.edit.stepsLabel')"
        :helper="t('cases.edit.linesHelper')"
        helper-placement="label"
        :rows="6"
        required
        :error="fieldErrors.stepsText"
      />
      <TpInput
        v-model="form.expectedText"
        as="textarea"
        :label="t('cases.edit.expectedLabel')"
        :helper="t('cases.edit.linesHelper')"
        helper-placement="label"
        :rows="6"
        required
        :error="fieldErrors.expectedText"
      />
      <div class="grid gap-4 md:grid-cols-2">
        <TpInput v-model="form.priority" as="select" :label="t('cases.table.columns.priority')" :options="priorityOptions" />
        <TpInput v-model="form.status" as="select" :label="t('cases.table.columns.status')" :options="statusOptions" />
      </div>
      <TpInput v-model="form.category" :label="t('cases.table.columns.category')" />
      <TpInput
        v-model="form.tagsText"
        :label="t('cases.table.columns.tags')"
        :helper="t('cases.edit.tagsHelper')"
        helper-placement="label"
        :placeholder="t('cases.edit.tagsPlaceholder')"
      />
    </div>

    <template v-if="activeRecord && !loading && !loadError" #footer>
      <form class="flex flex-wrap justify-end gap-2" novalidate @submit.prevent="handleSubmit">
        <TpButton variant="ghost" type="button" :disabled="saving" @click="emit('close')">
          {{ t('common.actions.cancel') }}
        </TpButton>
        <TpButton type="submit" :loading="saving" :disabled="saving">
          {{ t('common.actions.save') }}
        </TpButton>
      </form>
    </template>
  </FormSideDrawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import FormSideDrawer from '@/components/common/FormSideDrawer.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import { getCase, updateCase, type CaseRecord, type CaseUpdatePayload } from '@/api/cases';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { applyRequiredFieldErrors, isBlankField } from '@/lib/required-field';

interface SelectOption {
  value: string;
  label: string;
}

const props = defineProps<{
  visible: boolean;
  record: CaseRecord | null;
  priorityOptions: SelectOption[];
  statusOptions: SelectOption[];
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'saved', record: CaseRecord): void;
  (event: 'error', message: string): void;
}>();

const { t } = useI18n();
const saving = ref(false);
const loading = ref(false);
const loadError = ref('');
const loadedRecord = ref<CaseRecord | null>(null);

const activeRecord = computed(() => loadedRecord.value || props.record);

const form = reactive({
  title: '',
  description: '',
  precondition: '',
  module: '',
  testMethod: '',
  stepsText: '',
  expectedText: '',
  priority: 'P2',
  status: 'draft',
  category: '',
  tagsText: ''
});

const fieldErrors = reactive({ title: '', stepsText: '', expectedText: '' });

function resolveCaseId(row: CaseRecord) {
  return String(row.display_id || row.case_id || '').trim() || '-';
}

function linesToArray(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function tagsToArray(text: string) {
  return text
    .split(/[,，\n]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function arrayToLines(items: string[]) {
  return (items || []).filter(Boolean).join('\n');
}

function resetForm(record: CaseRecord | null) {
  if (!record) {
    form.title = '';
    form.description = '';
    form.precondition = '';
    form.module = '';
    form.testMethod = '';
    form.stepsText = '';
    form.expectedText = '';
    form.priority = 'P2';
    form.status = 'draft';
    form.category = '';
    form.tagsText = '';
    return;
  }
  form.title = record.title || '';
  form.description = record.description || '';
  form.precondition = record.precondition || '';
  form.module = record.module || '';
  form.testMethod = record.test_method || '';
  form.stepsText = arrayToLines(record.steps);
  form.expectedText = arrayToLines(record.expected_result);
  form.priority = String(record.priority || 'P2');
  form.status = String(record.status || 'draft');
  form.category = String(record.category || '');
  form.tagsText = (record.tags || []).join(', ');
}

async function loadDetail(caseId: string) {
  loading.value = true;
  loadError.value = '';
  loadedRecord.value = null;
  try {
    loadedRecord.value = await getCase(caseId);
    resetForm(loadedRecord.value);
  } catch (error) {
    loadError.value = getUserFacingErrorMessage(error, t('cases.message.loadFailed'));
    if (props.record) resetForm(props.record);
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.visible, props.record?.case_id] as const,
  ([open, caseId]) => {
    if (!open || !caseId) {
      loadedRecord.value = null;
      loadError.value = '';
      return;
    }
    void loadDetail(String(caseId));
  }
);

function validateCaseForm(): boolean {
  const baseOk = applyRequiredFieldErrors(fieldErrors, {
    title: form.title,
    stepsText: form.stepsText,
    expectedText: form.expectedText
  });
  const stepsRequiredMsg = t('cases.edit.stepsRequired');
  if (!isBlankField(form.stepsText) && !linesToArray(form.stepsText).length) {
    fieldErrors.stepsText = stepsRequiredMsg;
  }
  if (!isBlankField(form.expectedText) && !linesToArray(form.expectedText).length) {
    fieldErrors.expectedText = stepsRequiredMsg;
  }
  return (
    baseOk &&
    !fieldErrors.stepsText &&
    !fieldErrors.expectedText
  );
}

async function handleSubmit() {
  const caseId = activeRecord.value?.case_id;
  if (!caseId) return;
  if (!validateCaseForm()) return;

  const title = form.title.trim();
  const steps = linesToArray(form.stepsText);
  const expected_result = linesToArray(form.expectedText);

  const payload: CaseUpdatePayload = {
    title,
    description: form.description.trim(),
    precondition: form.precondition.trim(),
    module: form.module.trim(),
    test_method: form.testMethod.trim(),
    steps,
    expected_result,
    priority: form.priority,
    status: form.status,
    category: form.category.trim(),
    tags: tagsToArray(form.tagsText),
    updated_time: activeRecord.value?.updated_time ?? null
  };

  try {
    saving.value = true;
    const updated = await updateCase(caseId, payload);
    emit('saved', updated);
  } catch (error) {
    emit('error', getUserFacingErrorMessage(error, t('cases.message.updateFailed')));
  } finally {
    saving.value = false;
  }
}
</script>
