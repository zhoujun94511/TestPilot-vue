<template>
  <FormSideDrawer
    :open="visible"
    :title="title"
    :subtitle="subtitle || '-'"
    :aria-label="title"
    :dismissible="true"
    @close="emit('close')"
  >
    <template #header-actions>
      <div class="flex shrink-0 items-center gap-2">
        <TpButton v-if="copyable" variant="secondary" size="sm" :disabled="!content || loading" @click="handleCopy">
          {{ copied ? copiedText : copyText }}
        </TpButton>
        <TpButton variant="ghost" size="sm" @click="emit('close')">
          {{ closeText }}
        </TpButton>
      </div>
    </template>

    <template v-if="metaLine" #header-meta>
      {{ metaLine }}
    </template>

    <BaseState v-if="loading" variant="loading" :title="loadingTitle" />
    <BaseState v-else-if="error" variant="error" :title="errorTitle" :message="error" />
    <BaseState v-else-if="!content" variant="empty" :title="emptyTitle" />
    <pre v-else :class="previewDrawerContentClass">{{ content }}</pre>
  </FormSideDrawer>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import FormSideDrawer from '@/components/common/FormSideDrawer.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import { previewDrawerContentClass } from '@/lib/preview-drawer-ui';

const props = withDefaults(defineProps<{
  visible: boolean;
  title: string;
  subtitle?: string;
  metaLine?: string;
  content?: string;
  loading?: boolean;
  error?: string;
  emptyTitle?: string;
  loadingTitle?: string;
  errorTitle?: string;
  closeText?: string;
  copyText?: string;
  copiedText?: string;
  copyable?: boolean;
}>(), {
  subtitle: '',
  metaLine: '',
  content: '',
  loading: false,
  error: '',
  emptyTitle: '',
  loadingTitle: '',
  errorTitle: '',
  closeText: '',
  copyText: '',
  copiedText: '',
  copyable: false
});

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'copied'): void;
  (event: 'copyFailed'): void;
}>();

const { t } = useI18n();

const closeText = computed(() => props.closeText || t('common.actions.close'));
const emptyTitle = computed(() => props.emptyTitle || t('common.status.empty'));
const loadingTitle = computed(() => props.loadingTitle || t('common.status.loading'));
const errorTitle = computed(() => props.errorTitle || t('common.status.error'));
const copyText = computed(() => props.copyText || t('common.actions.copy'));
const copiedText = computed(() => props.copiedText || t('common.actions.copied'));
const copied = ref(false);
let copiedTimer: number | null = null;

async function handleCopy() {
  const text = String(props.content || '').trim();
  if (!text) return;
  try {
    await copyToClipboard(text);
    copied.value = true;
    if (copiedTimer) window.clearTimeout(copiedTimer);
    copiedTimer = window.setTimeout(() => {
      copied.value = false;
      copiedTimer = null;
    }, 1500);
    emit('copied');
  } catch {
    emit('copyFailed');
  }
}

async function copyToClipboard(text: string) {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.top = '-9999px';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copiedOk = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!copiedOk) {
    throw new Error('copy_failed');
  }
}

onUnmounted(() => {
  if (copiedTimer) {
    window.clearTimeout(copiedTimer);
    copiedTimer = null;
  }
});
</script>
