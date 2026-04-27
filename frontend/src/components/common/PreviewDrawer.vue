<template>
  <div
    v-if="visible"
    class="tp-preview-overlay"
    role="dialog"
    aria-modal="true"
    :aria-label="title"
    @click.self="emit('close')"
  >
    <div class="tp-preview-drawer tp-surface tp-p-3" @click.stop>
      <div class="tp-flex tp-justify-between tp-align-center tp-gap-2 tp-mb-2">
        <div>
          <div class="tp-card__title">{{ title }}</div>
          <div class="tp-card__subtitle">{{ subtitle || '-' }}</div>
          <div v-if="metaLine" class="tp-preview-meta">{{ metaLine }}</div>
        </div>
        <div class="tp-flex tp-align-center tp-gap-2">
          <TpButton v-if="copyable" variant="secondary" size="sm" :disabled="!content || loading" @click="handleCopy">
            {{ copied ? copiedText : copyText }}
          </TpButton>
          <TpButton variant="ghost" size="sm" @click="emit('close')">
            {{ closeText }}
          </TpButton>
        </div>
      </div>
      <div class="tp-preview-drawer__body">
        <BaseState v-if="loading" variant="loading" :title="loadingTitle" />
        <BaseState v-else-if="error" variant="error" :title="errorTitle" :message="error" />
        <BaseState v-else-if="!content" variant="empty" :title="emptyTitle" />
        <pre v-else class="tp-preview-content">{{ content }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import TpButton from '@/components/ui/base/TpButton.vue';

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
  // Prefer Clipboard API in secure contexts, fallback to execCommand for compatibility.
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

function handleEsc(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.visible) {
    emit('close');
  }
}

watch(() => props.visible, (nextVisible) => {
  if (nextVisible) {
    window.addEventListener('keydown', handleEsc);
    return;
  }
  window.removeEventListener('keydown', handleEsc);
}, { immediate: true });

onUnmounted(() => {
  window.removeEventListener('keydown', handleEsc);
  if (copiedTimer) {
    window.clearTimeout(copiedTimer);
    copiedTimer = null;
  }
});
</script>

<style scoped>
.tp-preview-overlay {
  position: fixed;
  top: var(--tp-preview-top-offset, 100px);
  right: 0;
  bottom: 0;
  left: 0;
  background: transparent;
  z-index: 1100;
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.tp-preview-drawer {
  width: min(42vw, 760px);
  min-width: 440px;
  margin-top: 12px;
  height: calc(100dvh - var(--tp-preview-top-offset, 100px) - 48px - 12px);
  max-height: calc(100dvh - var(--tp-preview-top-offset, 100px) - 48px - 12px);
  margin-bottom: 48px;
  border-radius: 0;
  border-top: 0;
  border-right: 0;
  border-bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  pointer-events: auto;
  box-shadow: -8px 0 22px rgba(0, 0, 0, 0.16);
}

.tp-preview-drawer__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}

.tp-preview-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  min-height: 0;
  height: 100%;
  max-height: none;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--tp-border-default) transparent;
  padding: 12px;
  border-radius: var(--tp-radius-md);
  background: var(--tp-bg-subtle);
  border: 1px solid var(--tp-border-default);
  color: var(--tp-color-text-600);
}

.tp-preview-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.tp-preview-content::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--tp-border-default) 85%, transparent);
  border-radius: 999px;
}

.tp-preview-content::-webkit-scrollbar-track {
  background: transparent;
}

.tp-preview-meta {
  margin-top: 2px;
  font-size: 12px;
  color: var(--tp-color-text-500);
}

@media (max-width: 1199px) {
  .tp-preview-overlay {
    top: 0;
    background: rgba(12, 18, 36, 0.28);
    pointer-events: auto;
  }

  .tp-preview-drawer {
    width: min(88vw, 680px);
    min-width: 0;
    height: 100dvh;
    max-height: 100dvh;
    margin-top: 0;
    margin-bottom: 0;
  }
}
</style>
