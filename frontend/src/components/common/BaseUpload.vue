<template>
  <div class="tp-upload-panel">
    <label class="tp-form-label">{{ label }}</label>
    <div class="tp-upload-panel__row">
      <input ref="inputRef" class="tp-upload-panel__native-input" type="file" :accept="accept" :multiple="multiple" @change="handleChange" />
      <div
        class="tp-upload-panel__selection"
        role="button"
        tabindex="0"
        @click="openFileDialog"
        @keydown.enter.prevent="openFileDialog"
        @keydown.space.prevent="openFileDialog"
      >
        {{ hasSelection ? fileSummary : emptyText }}
      </div>
      <button type="button" class="tp-upload-panel__picker" @click="openFileDialog">
        {{ chooseText }}
      </button>
      <TpButton :loading="loading" :disabled="loading || !hasSelection" @click="submit">
        {{ loading ? loadingText : submitText }}
      </TpButton>
    </div>
    <div class="tp-upload-panel__footer">
      <div class="tp-help-text">{{ hint }}</div>
      <TpButton v-if="hasSelection" variant="ghost" size="sm" @click="clear">
        {{ clearText }}
      </TpButton>
    </div>
    <div v-if="hasSelection" class="tp-upload-panel__filename">
      {{ fileSummary }}
    </div>
    <div v-else class="tp-upload-panel__filename">{{ emptyText }}</div>
    <slot name="after-filename"></slot>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import TpButton from '@/components/ui/base/TpButton.vue';

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
  if (props.loading) return;
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

function formatBytes(bytes: number) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}
</script>

<style scoped>
.tp-upload-panel__row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.tp-upload-panel__selection {
  flex: 1;
  min-width: 220px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-radius: var(--tp-radius-md);
  border: 1px solid var(--tp-border-default);
  background: var(--tp-bg-subtle);
  color: var(--tp-color-text-500);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.tp-upload-panel__selection:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--tp-color-primary-600) 60%, transparent);
  outline-offset: 1px;
}

.tp-upload-panel__native-input {
  display: none;
}

.tp-upload-panel__picker {
  flex: 0 0 auto;
  padding: 11px 12px;
  border-radius: var(--tp-radius-md);
  border: 1px solid var(--tp-border-default);
  background: var(--tp-bg-subtle);
  color: var(--tp-color-text-600);
  cursor: pointer;
  font-weight: 600;
}

@media (max-width: 767.98px) {
  .tp-upload-panel__row {
    flex-wrap: wrap;
  }

  .tp-upload-panel__selection {
    min-width: 0;
    width: 100%;
  }
}
</style>
