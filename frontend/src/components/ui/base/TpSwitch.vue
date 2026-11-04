<template>
  <div v-if="mode === 'field'" :class="switchFieldRoot()">
    <span v-if="label" :id="captionId" class="sr-only">{{ label }}</span>
    <input
      :id="switchId"
      type="checkbox"
      role="switch"
      class="peer sr-only focus-visible:outline-none"
      :checked="modelValue"
      :disabled="disabled"
      :aria-labelledby="hasCaption ? captionId : undefined"
      :aria-label="hasCaption ? undefined : resolvedStateText"
      @change="onToggle"
      @blur="emit('blur')"
    />
    <label :class="switchLabelInner({ on: modelValue })" :for="switchId">
      <span :class="switchTrack({ on: modelValue })" aria-hidden="true">
        <span :class="switchThumb({ on: modelValue })" />
      </span>
      <span
        v-if="showState"
        :class="switchStateBadge({ on: modelValue })"
        :aria-hidden="hasCaption ? 'true' : undefined"
      >
        {{ resolvedStateText }}
      </span>
    </label>
  </div>

  <label
    v-else
    :class="switchComposerRoot({ on: modelValue, disabled: Boolean(disabled) })"
    :for="switchId"
  >
    <input
      :id="switchId"
      type="checkbox"
      role="switch"
      class="sr-only focus-visible:outline-none"
      :checked="modelValue"
      :disabled="disabled"
      :aria-labelledby="hasCaption ? captionId : undefined"
      :aria-label="hasCaption ? undefined : resolvedStateText"
      @change="onToggle"
      @blur="emit('blur')"
    />
    <span :class="switchTrack({ on: modelValue })" aria-hidden="true">
      <span :class="switchThumb({ on: modelValue })" />
    </span>
    <span
      v-if="showState"
      :class="switchStateBadge({ on: modelValue })"
      :aria-hidden="hasCaption ? 'true' : undefined"
    >
      {{ resolvedStateText }}
    </span>
    <span v-if="hasCaption" :id="captionId" :class="switchCaption()">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';
import { useI18n } from 'vue-i18n';
import { chatSwitchStateLabel } from '@/composables/useChatPreferences';
import {
  switchCaption,
  switchComposerRoot,
  switchFieldRoot,
  switchLabelInner,
  switchStateBadge,
  switchThumb,
  switchTrack
} from '@/lib/switch-ui';

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    mode?: 'field' | 'composer';
    label?: string;
    switchId?: string;
    disabled?: boolean;
    showState?: boolean;
    stateText?: string;
  }>(),
  {
    mode: 'composer',
    showState: true
  }
);

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void;
  (event: 'blur'): void;
  (event: 'change', value: boolean): void;
}>();

const { locale } = useI18n();
const slots = useSlots();

const switchId = computed(
  () => props.switchId || `tp-switch-${Math.random().toString(36).slice(2, 10)}`
);

const captionId = computed(() => `${switchId.value}-caption`);

const hasCaption = computed(() => Boolean(props.label || slots.default));

const resolvedStateText = computed(() => {
  if (props.stateText) return props.stateText;
  return chatSwitchStateLabel(props.modelValue, locale.value);
});

function onToggle(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  emit('update:modelValue', checked);
  emit('change', checked);
}
</script>
