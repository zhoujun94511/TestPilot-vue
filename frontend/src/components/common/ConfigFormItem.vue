<template>
  <div class="config-form-item">
    <label class="tp-form-label tp-flex tp-justify-between tp-align-center tp-gap-2">
      <span>
        {{ label }}
        <span v-if="required" class="tp-field__required">*</span>
      </span>
      <span v-if="dirty" class="tp-tag tp-tag--warning tp-field__dirty">{{ t('config.form.dirty') }}</span>
    </label>

    <TpInput
      v-if="kind === 'string' || kind === 'password'"
      :model-value="modelValue"
      :type="kind === 'password' ? 'password' : 'text'"
      :placeholder="placeholder"
      @update:modelValue="onInput"
      @blur="emit('blur')"
    />

    <TpInput
      v-else-if="kind === 'number'"
      :model-value="modelValue"
      type="number"
      :placeholder="placeholder"
      @update:modelValue="onNumberInput"
      @blur="emit('blur')"
    />

    <TpInput
      v-else-if="kind === 'select'"
      as="select"
      :model-value="modelValue"
      :placeholder="placeholder"
      :options="options"
      @update:modelValue="onSelect"
      @blur="emit('blur')"
    />

    <div v-else-if="kind === 'boolean'" class="tp-switch">
      <input
        class="tp-switch__input"
        type="checkbox"
        role="switch"
        :checked="Boolean(modelValue)"
        :id="switchId"
        @change="onBoolean(($event.target as HTMLInputElement).checked)"
        @blur="emit('blur')"
      />
      <label class="tp-switch__label" :class="{ 'tp-switch__label--on': Boolean(modelValue) }" :for="switchId">
        <span class="tp-switch__track" aria-hidden="true">
          <span class="tp-switch__thumb"></span>
        </span>
        <span class="tp-switch__state" :class="{ 'tp-switch__state--on': Boolean(modelValue) }">
          {{ switchStateLabel(Boolean(modelValue)) }}
        </span>
      </label>
    </div>

    <TpInput
      v-else
      as="textarea"
      :model-value="modelValue"
      :placeholder="placeholder"
      @update:modelValue="onInput"
      @blur="emit('blur')"
    />

    <div v-if="helper || error" class="tp-mt-2">
      <small v-if="helper" class="tp-help-text tp-d-block">{{ helper }}</small>
      <small v-if="error" class="tp-d-block" style="color: var(--tp-color-danger-600)">{{ error }}</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ConfigFieldKind, ConfigOption } from '@/api/config';
import TpInput from '@/components/ui/base/TpInput.vue';

const props = defineProps<{
  modelValue: string | number | boolean | null;
  kind: ConfigFieldKind;
  label: string;
  placeholder?: string;
  helper?: string;
  error?: string;
  dirty?: boolean;
  required?: boolean;
  options?: ConfigOption[];
  switchKey?: string;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number | boolean | null): void;
  (event: 'blur'): void;
}>();

const { t, locale } = useI18n();

const switchId = computed(() => props.switchKey || `cfg-switch-${Math.random().toString(36).slice(2, 10)}`);

function onInput(value: unknown) {
  emit('update:modelValue', value as string | number | boolean | null);
}

function onNumberInput(value: unknown) {
  const nextValue = String(value ?? '');
  if (nextValue === '') {
    emit('update:modelValue', null);
    return;
  }
  const next = Number(nextValue);
  emit('update:modelValue', Number.isNaN(next) ? nextValue : next);
}

function onSelect(value: unknown) {
  const nextValue = String(value ?? '');
  const matched = props.options?.find((option) => String(option.value) === nextValue);
  emit('update:modelValue', matched ? matched.value : nextValue);
}

function onBoolean(value: boolean) {
  emit('update:modelValue', value);
}

function switchStateLabel(enabled: boolean) {
  const isZh = String(locale.value || '').toLowerCase().startsWith('zh');
  if (isZh) return enabled ? '开' : '关';
  return enabled ? 'ON' : 'OFF';
}
</script>

<style scoped>
.tp-switch {
  display: flex;
  align-items: center;
  width: fit-content;
  min-width: 120px;
}

.tp-switch__input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.tp-switch__label {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 4px 6px 4px 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-bg-surface) 86%, var(--tp-color-text-100) 14%);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.tp-switch__track {
  width: 48px;
  height: 28px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-color-text-300) 86%, transparent);
  border: 1px solid var(--tp-border-default);
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.tp-switch__thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tp-bg-surface);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.18);
  transition: transform 0.2s ease;
}

.tp-switch__state {
  min-width: 34px;
  text-align: center;
  color: var(--tp-color-text-500);
  font-size: 11px;
  line-height: 1;
  font-weight: 700;
  padding: 4px 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--tp-color-text-300) 70%, transparent);
  background: color-mix(in srgb, var(--tp-color-text-200) 60%, transparent);
}

.tp-switch__state--on {
  color: var(--tp-color-primary-700);
  border-color: color-mix(in srgb, var(--tp-color-primary-500) 60%, transparent);
  background: color-mix(in srgb, var(--tp-color-primary-500) 20%, transparent);
}

.tp-switch__label--on .tp-switch__track {
  background: var(--tp-color-primary-500);
  border-color: var(--tp-color-primary-600);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--tp-color-primary-500) 26%, transparent);
}

.tp-switch__label--on .tp-switch__thumb {
  transform: translateX(20px);
}

.tp-switch__label--on {
  background: color-mix(in srgb, var(--tp-color-primary-500) 10%, var(--tp-bg-surface) 90%);
}

.tp-switch__input:focus-visible + .tp-switch__label .tp-switch__track {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tp-color-primary-500) 22%, transparent);
}
</style>
