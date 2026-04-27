<template>
  <div class="tp-field">
    <label v-if="label" class="tp-form-label" :for="inputId">
      {{ label }}
      <span v-if="required" class="tp-field__required">*</span>
    </label>

    <input
      v-if="as === 'input'"
      :id="inputId"
      class="tp-input"
      :type="type"
      :value="modelValue ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      :autocomplete="autocomplete"
      @input="emitValue(($event.target as HTMLInputElement).value)"
      @blur="emit('blur')"
    />

    <textarea
      v-else-if="as === 'textarea'"
      :id="inputId"
      class="tp-textarea"
      :rows="rows"
      :value="modelValue ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="emitValue(($event.target as HTMLTextAreaElement).value)"
      @blur="emit('blur')"
    />

    <select
      v-else-if="as === 'select'"
      :id="inputId"
      class="tp-select"
      :value="String(modelValue ?? '')"
      :disabled="disabled"
      @change="emitSelect(($event.target as HTMLSelectElement).value)"
      @blur="emit('blur')"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="String(option.value)" :value="String(option.value)">
        {{ option.label }}
      </option>
    </select>

    <slot v-else />

    <div v-if="helper || error" class="tp-field__meta">
      <div v-if="helper" class="tp-help-text">{{ helper }}</div>
      <div v-if="error" class="tp-field__error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type FieldKind = 'input' | 'textarea' | 'select';

interface SelectOption {
  value: string | number | boolean;
  label: string;
}

const props = withDefaults(defineProps<{
  modelValue: string | number | boolean | null;
  label?: string;
  placeholder?: string;
  helper?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  as?: FieldKind;
  type?: string;
  rows?: number;
  autocomplete?: string;
  options?: SelectOption[];
  inputId?: string;
}>(), {
  as: 'input',
  type: 'text',
  rows: 4
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number | boolean | null): void;
  (event: 'blur'): void;
}>();

const inputId = computed(() => props.inputId || `tp-field-${Math.random().toString(36).slice(2, 10)}`);

function emitValue(value: string) {
  emit('update:modelValue', value);
}

function emitSelect(value: string) {
  const matched = props.options?.find((option) => String(option.value) === value);
  emit('update:modelValue', matched ? matched.value : value);
}
</script>

<style scoped>
.tp-field {
  display: grid;
  gap: 0;
}

.tp-field__required {
  color: var(--tp-color-danger-600);
}

.tp-field__meta {
  margin-top: 6px;
}

.tp-field__error {
  margin-top: 4px;
  font-size: 0.78rem;
  color: var(--tp-color-danger-600);
}
</style>
