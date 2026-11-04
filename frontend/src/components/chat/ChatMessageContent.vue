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

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
  highlight(code, language) {
    const escaped = escapeHtml(code);
    const lineCount = String(code || '').split(/\r?\n/).length;
    const shouldToggle = lineCount > 12;
    const lang = String(language || '').trim();
    const langLabel = lang || 'text';
    const langClass = lang ? `language-${escapeHtml(lang)}` : 'language-text';
    return `<div class="chat-rich-content__code-wrap">
      <div class="chat-rich-content__code-head">
        <div class="chat-rich-content__code-lang">${escapeHtml(langLabel)}</div>
        <div class="chat-rich-content__code-actions">
          ${shouldToggle
    ? `<button type="button" class="chat-rich-content__copy-btn" data-role="toggle-code" data-expanded="false">${escapeHtml(String(t('chat.richContent.expand')))}</button>`
    : ''}
          <button type="button" class="chat-rich-content__copy-btn" data-role="copy-code">${escapeHtml(String(t('chat.richContent.copy')))}</button>
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
