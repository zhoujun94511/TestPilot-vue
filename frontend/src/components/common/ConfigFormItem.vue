<template>
  <div class="config-form-item min-w-0 max-w-full">
    <label :class="cn(formLabelClass, 'mb-0 w-full justify-between')">
      <span>
        {{ label }}
        <span v-if="required" :class="fieldRequiredMarkClass">*</span>
      </span>
      <TpTag v-if="dirty" variant="warning" :class="fieldDirtyTagClass">{{ t('config.form.dirty') }}</TpTag>
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

    <TpSwitch
      v-else-if="kind === 'boolean'"
      :model-value="Boolean(modelValue)"
      mode="field"
      :switch-id="switchId"
      :label="Boolean(modelValue) ? t('config.form.enabled') : t('config.form.disabled')"
      @update:model-value="onBoolean"
      @blur="emit('blur')"
    />

    <div v-else-if="kind === 'dedup_weights'" class="grid min-w-0 gap-3 sm:grid-cols-2">
      <div v-for="weightKey in dedupWeightKeys" :key="weightKey" class="min-w-0">
        <label :class="[formLabelClass, 'mb-1.5 text-xs']">
          {{ t(`config.form.dedupWeights.${weightKey}`) }}
        </label>
        <TpInput
          bare
          :model-value="dedupWeights[weightKey]"
          type="number"
          step="0.01"
          min="0"
          max="1"
          :placeholder="t('config.form.numberPlaceholder')"
          @update:modelValue="(v) => onDedupWeight(weightKey, v)"
          @blur="emit('blur')"
        />
      </div>
    </div>

    <TpInput
      v-else
      as="textarea"
      :model-value="modelValue"
      :placeholder="placeholder"
      @update:modelValue="onInput"
      @blur="emit('blur')"
    />

    <div v-if="helper || error" :class="configFormFieldFootClass">
      <small v-if="helper" :class="configFormHelpTextClass">{{ helper }}</small>
      <small v-if="error" :class="configFormErrorTextClass">{{ error }}</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ConfigFieldKind, ConfigOption, ContentDedupWeightKey } from '@/api/config';
import {
  CONTENT_DEDUP_WEIGHT_KEYS,
  parseContentDedupWeights,
  serializeContentDedupWeights
} from '@/api/config';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpSwitch from '@/components/ui/base/TpSwitch.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  configFormErrorTextClass,
  configFormFieldFootClass,
  configFormHelpTextClass
} from '@/lib/config-ui';
import {
  fieldDirtyTagClass,
  fieldRequiredMarkClass,
  formLabelClass
} from '@/lib/field-control';
import { cn } from '@/lib/utils';

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

const { t } = useI18n();

const switchId = computed(() => props.switchKey || `cfg-switch-${Math.random().toString(36).slice(2, 10)}`);

const dedupWeightKeys = CONTENT_DEDUP_WEIGHT_KEYS;

const dedupWeights = computed(() => parseContentDedupWeights(props.modelValue));

function onDedupWeight(key: ContentDedupWeightKey, value: unknown) {
  const next = { ...dedupWeights.value };
  const n = Number(value);
  next[key] = Number.isNaN(n) ? 0 : n;
  emit('update:modelValue', serializeContentDedupWeights(next));
}

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
</script>
