<template>
  <div :class="uploadPanelClass">
    <label :class="formLabelClass">{{ label }}</label>
    <div :class="uploadPanelRowClass">
      <input
        ref="inputRef"
        :class="uploadPanelNativeInputClass"
        type="file"
        :accept="accept"
        :multiple="multiple"
        @change="handleChange"
      />
      <div
        :class="uploadPanelSelectionClass"
        role="button"
        :tabindex="isBlocked ? -1 : 0"
        :aria-disabled="isBlocked"
        @click="openFileDialog"
        @keydown.enter.prevent="openFileDialog"
        @keydown.space.prevent="openFileDialog"
      >
        {{ hasSelection ? fileSummary : emptyText }}
      </div>
      <button
        type="button"
        :class="uploadPanelPickerClass"
        :disabled="isBlocked"
        @click="openFileDialog"
      >
        {{ chooseText }}
      </button>
      <TpButton :loading="loading" :disabled="isBlocked || !hasSelection" @click="submit">
        {{ loading ? loadingText : submitText }}
      </TpButton>
    </div>
    <div :class="uploadPanelFooterClass">
      <div :class="helpTextClass">{{ hint }}</div>
      <TpButton v-if="hasSelection" variant="ghost" size="sm" @click="clear">
        {{ clearText }}
      </TpButton>
    </div>
    <div v-if="hasSelection" :class="uploadPanelFilenameClass">
      {{ fileSummary }}
    </div>
    <div v-else :class="uploadPanelFilenameClass">{{ emptyText }}</div>
    <slot name="after-filename"></slot>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import { formLabelClass, helpTextClass } from '@/lib/field-control';
import {
  uploadPanelClass,
  uploadPanelFilenameClass,
  uploadPanelFooterClass,
  uploadPanelNativeInputClass,
  uploadPanelPickerClass,
  uploadPanelRowClass,
  uploadPanelSelectionClass
} from '@/lib/upload-ui';
import { formatBytes } from '@/lib/format';

const props = defineProps<{
  modelValue: File | File[] | null;
  label: string;
  chooseText: string;
  submitText: string;
  loadingText: string;
  hint: string;
  emptyText: string;
  clearText: string;
  accept?: string;
  loading?: boolean;
  multiple?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: File | File[] | null): void;
  (event: 'submit', file: File | File[]): void;
  (event: 'change', file: File | File[] | null): void;
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const selectedFiles = computed<File[]>(() => {
  if (!props.modelValue) return [];
  return Array.isArray(props.modelValue) ? props.modelValue : [props.modelValue];
});
const hasSelection = computed(() => selectedFiles.value.length > 0);
const isBlocked = computed(() => Boolean(props.loading || props.disabled));
const fileSummary = computed(() => {
  if (!selectedFiles.value.length) return '';
  if (selectedFiles.value.length === 1) {
    const file = selectedFiles.value[0];
    return `${file.name} - ${formatBytes(file.size)}`;
  }
  const totalSize = selectedFiles.value.reduce((sum, file) => sum + (file.size || 0), 0);
  return `${selectedFiles.value.length} files - ${formatBytes(totalSize)}`;
});

function openFileDialog() {
  if (isBlocked.value) return;
  inputRef.value?.click();
}

function handleChange(event: Event) {
  const input = event.target as HTMLInputElement;
  if (props.multiple) {
    const files = input.files ? Array.from(input.files) : [];
    emit('update:modelValue', files);
    emit('change', files);
    return;
  }

  const file = input.files?.[0] ?? null;
  emit('update:modelValue', file);
  emit('change', file);
}

function submit() {
  if (!hasSelection.value) return;
  if (props.multiple) {
    emit('submit', selectedFiles.value);
    return;
  }
  emit('submit', selectedFiles.value[0]);
}

function clear() {
  if (props.multiple) {
    emit('update:modelValue', []);
    emit('change', []);
  } else {
    emit('update:modelValue', null);
    emit('change', null);
  }
  if (inputRef.value) inputRef.value.value = '';
}

watch(selectedFiles, (next) => {
  if (next.length === 0 && inputRef.value) {
    inputRef.value.value = '';
  }
});

</script>
