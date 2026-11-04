<template>
  <div v-if="!bare" :class="fieldRootClass">
    <label
      v-if="label"
      :class="cn(formLabelClass, helper && resolvedHelperPlacement === 'label' && 'mb-1')"
      :for="inputId"
    >
      {{ label }}
      <span v-if="required" :class="fieldRequiredMarkClass">*</span>
    </label>

    <div v-if="helper && resolvedHelperPlacement === 'label'" :class="helpTextBelowLabelClass">
      {{ helper }}
    </div>

    <input
      v-if="as === 'input'"
      :id="inputId"
      :class="mergeControlSizeClass(inputVariants(), controlClass)"
      :type="type"
      :value="modelValue ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-required="required ? 'true' : undefined"
      :autocomplete="autocomplete"
      v-bind="controlAttrs"
      @input="emitValue(($event.target as HTMLInputElement).value)"
      @blur="emit('blur')"
      @keydown="emit('keydown', $event)"
    />

    <textarea
      v-else-if="as === 'textarea'"
      :id="inputId"
      :class="cn(textareaVariants(), controlClass)"
      :rows="rows"
      :value="String(modelValue ?? '')"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-required="required ? 'true' : undefined"
      v-bind="controlAttrs"
      @input="emitValue(($event.target as HTMLTextAreaElement).value)"
      @blur="emit('blur')"
      @keydown="emit('keydown', $event)"
    />

    <select
      v-else-if="as === 'select'"
      :id="inputId"
      :class="mergeControlSizeClass(selectVariants(), controlClass)"
      :value="String(modelValue ?? '')"
      :disabled="disabled"
      v-bind="controlAttrs"
      @change="emitSelect(($event.target as HTMLSelectElement).value)"
      @blur="emit('blur')"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="String(option.value)" :value="String(option.value)">
        {{ option.label }}
      </option>
    </select>

    <slot v-else />

    <div v-if="(helper && resolvedHelperPlacement === 'field') || error" :class="fieldMetaClass">
      <div v-if="helper && resolvedHelperPlacement === 'field'" :class="helpTextBelowFieldClass">{{ helper }}</div>
      <div v-if="error" :class="fieldErrorTextClass">{{ error }}</div>
    </div>
  </div>

  <template v-else>
    <input
      v-if="as === 'input'"
      :id="inputId"
      :class="mergeControlSizeClass(inputVariants(), controlClass)"
      :type="type"
      :value="modelValue ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-required="required ? 'true' : undefined"
      :autocomplete="autocomplete"
      v-bind="controlAttrs"
      @input="emitValue(($event.target as HTMLInputElement).value)"
      @blur="emit('blur')"
      @keydown="emit('keydown', $event)"
    />

    <textarea
      v-else-if="as === 'textarea'"
      :id="inputId"
      :class="cn(textareaVariants(), controlClass)"
      :rows="rows"
      :value="String(modelValue ?? '')"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-required="required ? 'true' : undefined"
      v-bind="controlAttrs"
      @input="emitValue(($event.target as HTMLTextAreaElement).value)"
      @blur="emit('blur')"
      @keydown="emit('keydown', $event)"
    />

    <select
      v-else-if="as === 'select'"
      :id="inputId"
      :class="mergeControlSizeClass(selectVariants(), controlClass)"
      :value="String(modelValue ?? '')"
      :disabled="disabled"
      v-bind="controlAttrs"
      @change="emitSelect(($event.target as HTMLSelectElement).value)"
      @blur="emit('blur')"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="String(option.value)" :value="String(option.value)">
        {{ option.label }}
      </option>
    </select>

    <slot v-else />
  </template>
</template>

<script setup lang="ts">
import type { HTMLAttributes, InputHTMLAttributes } from 'vue';
import { computed, useAttrs } from 'vue';
import { cn } from '@/lib/utils';
import {
  fieldErrorTextClass,
  fieldMetaClass,
  fieldRequiredMarkClass,
  fieldRootClass,
  formLabelClass,
  helpTextBelowFieldClass,
  helpTextBelowLabelClass,
  inputVariants,
  mergeControlSizeClass,
  selectVariants,
  textareaVariants
} from '@/lib/field-control';

defineOptions({ inheritAttrs: false });

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
  /** label：说明紧贴标签、在输入框上方；field：说明在控件下方（默认） */
  helperPlacement?: 'label' | 'field';
  error?: string;
  required?: boolean;
  disabled?: boolean;
  bare?: boolean;
  as?: FieldKind;
  type?: string;
  rows?: number;
  autocomplete?: string;
  options?: SelectOption[];
  inputId?: string;
  controlClass?: HTMLAttributes['class'];
}>(), {
  as: 'input',
  type: 'text',
  rows: 4,
  bare: false
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number | boolean | null): void;
  (event: 'blur'): void;
  (event: 'keydown', payload: KeyboardEvent): void;
}>();

const attrs = useAttrs();
/** 不把 HTML required 传给原生控件，避免浏览器按系统语言弹出校验气泡 */
const controlAttrs = computed(() => {
  const raw = { ...(attrs as Record<string, unknown>) };
  delete raw.required;
  return raw as InputHTMLAttributes;
});

const inputId = computed(() => props.inputId || `tp-field-${Math.random().toString(36).slice(2, 10)}`);

/** 多行输入默认把 helper 放在标签与控件之间，避免大框把说明顶到页面底部 */
const resolvedHelperPlacement = computed((): 'label' | 'field' => {
  if (props.helperPlacement === 'label' || props.helperPlacement === 'field') {
    return props.helperPlacement;
  }
  if (props.as === 'textarea' && props.helper) {
    return 'label';
  }
  return 'field';
});

function emitValue(value: string) {
  if (props.type === 'number') {
    if (value === '') {
      emit('update:modelValue', null);
      return;
    }
    const next = Number(value);
    emit('update:modelValue', Number.isNaN(next) ? value : next);
    return;
  }
  emit('update:modelValue', value);
}

function emitSelect(value: string) {
  const matched = props.options?.find((option) => String(option.value) === value);
  emit('update:modelValue', matched ? matched.value : value);
}
</script>
