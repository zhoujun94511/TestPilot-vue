<template>
  <div class="chat-rich-content" @click="handleContentClick" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';

const props = defineProps<{
  content: string;
  role?: 'user' | 'assistant' | 'system';
}>();
const { t } = useI18n();

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
  highlight(code, language) {
    const escaped = markdown.utils.escapeHtml(code);
    const lineCount = String(code || '').split(/\r?\n/).length;
    const shouldToggle = lineCount > 12;
    const lang = String(language || '').trim();
    const langLabel = lang || 'text';
    const langClass = lang ? `language-${markdown.utils.escapeHtml(lang)}` : 'language-text';
    return `<div class="chat-rich-content__code-wrap">
      <div class="chat-rich-content__code-head">
        <div class="chat-rich-content__code-lang">${markdown.utils.escapeHtml(langLabel)}</div>
        <div class="chat-rich-content__code-actions">
          ${shouldToggle
    ? `<button type="button" class="chat-rich-content__copy-btn" data-role="toggle-code" data-expanded="false">${markdown.utils.escapeHtml(String(t('chat.richContent.expand')))}</button>`
    : ''}
          <button type="button" class="chat-rich-content__copy-btn" data-role="copy-code">${markdown.utils.escapeHtml(String(t('chat.richContent.copy')))}</button>
        </div>
      </div>
      <pre class="chat-rich-content__code ${shouldToggle ? 'chat-rich-content__code--collapsed' : ''}"><code class="${langClass}">${escaped}</code></pre>
    </div>`;
  }
});

const defaultLinkRender = markdown.renderer.rules.link_open
  || ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options));
markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet('target', '_blank');
  tokens[idx].attrSet('rel', 'noopener noreferrer');
  return defaultLinkRender(tokens, idx, options, env, self);
};

markdown.renderer.rules.table_open = () => `<div class="chat-rich-content__table-wrap">
  <div class="chat-rich-content__table-hint">${markdown.utils.escapeHtml(String(t('chat.richContent.tableHint')))}</div>
  <table class="chat-rich-content__table">`;
markdown.renderer.rules.table_close = () => '</table></div>';

const renderedHtml = computed(() => {
  const raw = markdown.render(String(props.content || ''));
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel', 'class', 'data-role']
  });
});

async function handleContentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (!target) return;
  const toggleButton = target.closest('[data-role="toggle-code"]') as HTMLButtonElement | null;
  if (toggleButton) {
    const wrapper = toggleButton.closest('.chat-rich-content__code-wrap');
    const codeBlock = wrapper?.querySelector('.chat-rich-content__code') as HTMLElement | null;
    if (!codeBlock) return;
    const expanded = toggleButton.dataset.expanded === 'true';
    codeBlock.classList.toggle('chat-rich-content__code--collapsed', expanded);
    codeBlock.classList.toggle('chat-rich-content__code--expanded', !expanded);
    toggleButton.dataset.expanded = expanded ? 'false' : 'true';
    toggleButton.textContent = String(expanded ? t('chat.richContent.expand') : t('chat.richContent.collapse'));
    return;
  }
  const copyButton = target.closest('[data-role="copy-code"]') as HTMLButtonElement | null;
  if (!copyButton) return;

  const wrapper = copyButton.closest('.chat-rich-content__code-wrap');
  const codeElement = wrapper?.querySelector('code');
  const text = codeElement?.textContent || '';
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    copyButton.textContent = String(t('chat.richContent.copied'));
    window.setTimeout(() => {
      copyButton.textContent = String(t('chat.richContent.copy'));
    }, 1200);
  } catch {
    copyButton.textContent = String(t('chat.richContent.copyFailed'));
    window.setTimeout(() => {
      copyButton.textContent = String(t('chat.richContent.copy'));
    }, 1200);
  }
}
</script>

<style scoped>
.chat-rich-content {
  display: grid;
  gap: 10px;
  animation: tp-chat-content-fade-in 120ms ease-out;
  min-width: 0;
}

.chat-rich-content :deep(p) {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.6;
}

.chat-rich-content :deep(h1),
.chat-rich-content :deep(h2),
.chat-rich-content :deep(h3),
.chat-rich-content :deep(h4),
.chat-rich-content :deep(h5),
.chat-rich-content :deep(h6) {
  margin: 6px 0 2px;
  line-height: 1.4;
}

.chat-rich-content :deep(blockquote) {
  margin: 0;
  padding: 8px 10px;
  border-left: 3px solid var(--tp-color-primary-600);
  background: var(--tp-bg-subtle);
}

.chat-rich-content :deep(ul),
.chat-rich-content :deep(ol) {
  margin: 0;
  padding-left: 20px;
  min-width: 0;
}

.chat-rich-content :deep(li + li) {
  margin-top: 4px;
}

.chat-rich-content :deep(hr) {
  margin: 4px 0;
  border: 0;
  border-top: 1px solid var(--tp-border-default);
}

.chat-rich-content :deep(a) {
  color: var(--tp-color-primary-600);
  text-decoration: underline;
  text-underline-offset: 2px;
  word-break: break-all;
  overflow-wrap: anywhere;
}

.chat-rich-content :deep(code:not(pre code)) {
  display: inline-block;
  padding: 1px 5px;
  border-radius: var(--tp-radius-sm);
  border: 1px solid var(--tp-border-default);
  background: var(--tp-bg-subtle);
  font-size: 0.92em;
}

.chat-rich-content :deep(.chat-rich-content__code-wrap) {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  background: var(--tp-bg-surface);
  background: color-mix(in srgb, var(--tp-bg-surface) 88%, #000 12%);
  overflow: hidden;
}

.chat-rich-content :deep(.chat-rich-content__code-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--tp-border-default);
}

.chat-rich-content :deep(.chat-rich-content__code-actions) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 6px 4px auto;
}

.chat-rich-content :deep(.chat-rich-content__code-lang) {
  padding: 6px 10px;
  color: var(--tp-color-text-500);
  font-size: 12px;
  text-transform: lowercase;
}

.chat-rich-content :deep(.chat-rich-content__copy-btn) {
  margin: 0;
  padding: 2px 8px;
  border-radius: var(--tp-radius-sm);
  border: 1px solid var(--tp-border-default);
  background: var(--tp-bg-surface);
  color: var(--tp-color-text-700);
  font-size: 12px;
  cursor: pointer;
}

.chat-rich-content :deep(.chat-rich-content__copy-btn:hover) {
  background: var(--tp-bg-subtle);
}

.chat-rich-content :deep(.chat-rich-content__copy-btn:focus-visible) {
  outline: 2px solid var(--tp-color-primary-500);
  outline-offset: 2px;
}

.chat-rich-content :deep(.chat-rich-content__code) {
  margin: 0;
  padding: 10px 12px;
  overflow-x: auto;
  white-space: pre;
  line-height: 1.5;
  max-width: 100%;
}

.chat-rich-content :deep(.chat-rich-content__code--collapsed) {
  max-height: 220px;
  overflow-y: auto;
}

.chat-rich-content :deep(.chat-rich-content__code--expanded) {
  max-height: 560px;
  overflow-y: auto;
}

.chat-rich-content :deep(.chat-rich-content__table-wrap) {
  overflow-x: auto;
  max-width: 100%;
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  background: var(--tp-bg-surface);
}

.chat-rich-content :deep(.chat-rich-content__table-hint) {
  padding: 6px 10px;
  border-bottom: 1px dashed var(--tp-border-default);
  font-size: 12px;
  color: var(--tp-color-text-500);
  background: var(--tp-bg-subtle);
}

.chat-rich-content :deep(.chat-rich-content__table) {
  width: 100%;
  min-width: 420px;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.chat-rich-content :deep(.chat-rich-content__table th),
.chat-rich-content :deep(.chat-rich-content__table td) {
  padding: 8px 10px;
  border-bottom: 1px solid var(--tp-border-default);
  border-right: 1px solid var(--tp-border-default);
  text-align: left;
  vertical-align: top;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .chat-rich-content {
    gap: 8px;
  }

  .chat-rich-content :deep(.chat-rich-content__table) {
    min-width: 320px;
    font-size: 12px;
  }

  .chat-rich-content :deep(.chat-rich-content__code) {
    padding: 8px 10px;
    font-size: 12px;
  }
}

.chat-rich-content :deep(.chat-rich-content__table th) {
  background: var(--tp-bg-subtle);
  color: var(--tp-color-text-800);
  font-weight: 600;
}

.chat-rich-content :deep(.chat-rich-content__table th:last-child),
.chat-rich-content :deep(.chat-rich-content__table td:last-child) {
  border-right: 0;
}

.chat-rich-content :deep(.chat-rich-content__table tbody tr:last-child td) {
  border-bottom: 0;
}

@keyframes tp-chat-content-fade-in {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
