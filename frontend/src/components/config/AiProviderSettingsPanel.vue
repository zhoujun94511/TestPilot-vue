<template>
  <section class="tp-provider-panel">
    <div class="tp-provider-panel__head">
      <div class="tp-card__title">{{ t('configCenter.providerUi.title') }}</div>
      <div class="tp-config-meta">{{ t('configCenter.providerUi.subtitle') }}</div>
    </div>

    <div class="tp-provider-grid">
      <article
        v-for="provider in providers"
        :key="provider.key"
        class="tp-provider-card"
        :class="{ 'tp-provider-card--active': provider.key === activeProvider }"
      >
        <header class="tp-provider-card__header">
          <div>
            <div class="tp-provider-card__title">{{ t(provider.nameKey) }}</div>
            <div class="tp-provider-card__status">
              {{ provider.key === activeProvider ? t('configCenter.providerUi.active') : t('configCenter.providerUi.inactive') }}
            </div>
          </div>
          <label class="tp-provider-switch">
            <input
              type="checkbox"
              class="sr-only"
              :checked="provider.key === activeProvider"
              @change="handleActivate(provider.key)"
            />
            <span class="tp-provider-switch__track">
              <span class="tp-provider-switch__dot" />
            </span>
          </label>
        </header>

        <div class="tp-provider-card__body">
          <label class="tp-provider-field">
            <span>{{ t('configCenter.providerUi.apiKey') }}</span>
            <input
              :value="provider.apiKey"
              class="tp-provider-input"
              type="password"
              :placeholder="t('configCenter.providerUi.apiKeyPlaceholder')"
              @input="handleApiKeyInput(provider.key, $event)"
            />
          </label>

          <div class="tp-provider-field">
            <span>{{ t('configCenter.providerUi.modelSelection') }}</span>
            <div class="tp-model-grid">
              <button
                v-for="model in provider.models"
                :key="model.id"
                type="button"
                class="tp-model-chip"
                :class="{ 'tp-model-chip--active': model.selected }"
                @click="handleToggleModel(provider.key, model.id)"
              >
                <span class="tp-model-chip__name">{{ model.name }}</span>
                <span class="tp-model-chip__desc">{{ t(model.descriptionKey) }}</span>
              </button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div class="tp-config-meta tp-mt-2">{{ t('configCenter.providerUi.saveHint') }}</div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

type ProviderKey = 'OPENAI' | 'GEMINI' | 'DEEPSEEK' | 'QWEN' | 'OLLAMA';

interface ProviderModel {
  id: string;
  name: string;
  descriptionKey: string;
  selected: boolean;
}

interface ProviderItem {
  key: ProviderKey;
  nameKey: string;
  apiKey: string;
  models: ProviderModel[];
}

const STORAGE_KEY = 'testpilot_ai_provider_settings_v1';
const { t } = useI18n();

const activeProvider = ref<ProviderKey>('OPENAI');
const providers = ref<ProviderItem[]>(buildDefaults());

hydrate();

function buildDefaults(): ProviderItem[] {
  return [
    {
      key: 'OPENAI',
      nameKey: 'configCenter.provider.OPENAI',
      apiKey: '',
      models: [
        { id: 'gpt-5', name: 'GPT-5', descriptionKey: 'configCenter.providerUi.modelDescriptions.gpt5', selected: true },
        { id: 'gpt-4o', name: 'GPT-4o', descriptionKey: 'configCenter.providerUi.modelDescriptions.gpt4o', selected: false }
      ]
    },
    {
      key: 'GEMINI',
      nameKey: 'configCenter.provider.GEMINI',
      apiKey: '',
      models: [
        { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash', descriptionKey: 'configCenter.providerUi.modelDescriptions.gemini38Flash', selected: true }
      ]
    },
    {
      key: 'DEEPSEEK',
      nameKey: 'configCenter.provider.DEEPSEEK',
      apiKey: '',
      models: [
        { id: 'deepseek-flash', name: 'DeepSeek Flash', descriptionKey: 'configCenter.providerUi.modelDescriptions.deepseekFlash', selected: true }
      ]
    },
    {
      key: 'QWEN',
      nameKey: 'configCenter.provider.QWEN',
      apiKey: '',
      models: [{ id: 'qwen-max', name: 'Qwen Max', descriptionKey: 'configCenter.providerUi.modelDescriptions.qwenMax', selected: true }]
    },
    {
      key: 'OLLAMA',
      nameKey: 'configCenter.providerUi.providerLabels.ollamaLocal',
      apiKey: '',
      models: [
        { id: 'llama3', name: 'Llama 3', descriptionKey: 'configCenter.providerUi.modelDescriptions.llama3', selected: true },
        { id: 'mistral', name: 'Mistral', descriptionKey: 'configCenter.providerUi.modelDescriptions.mistral', selected: false }
      ]
    }
  ];
}

function hydrate() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as { activeProvider?: ProviderKey; providers?: ProviderItem[] };
    if (parsed.activeProvider) {
      activeProvider.value = parsed.activeProvider;
    }
    if (Array.isArray(parsed.providers) && parsed.providers.length) {
      providers.value = parsed.providers;
    }
  } catch {
    // ignore malformed local storage data
  }
}

function persist() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      activeProvider: activeProvider.value,
      providers: providers.value
    })
  );
}

function handleActivate(key: ProviderKey) {
  activeProvider.value = key;
  persist();
}

function handleToggleModel(providerKey: ProviderKey, modelId: string) {
  const provider = providers.value.find((item) => item.key === providerKey);
  if (!provider) return;
  const target = provider.models.find((item) => item.id === modelId);
  if (!target) return;
  target.selected = !target.selected;
  persist();
}

function handleApiKeyInput(providerKey: ProviderKey, event: Event) {
  const provider = providers.value.find((item) => item.key === providerKey);
  if (!provider) return;
  provider.apiKey = (event.target as HTMLInputElement).value;
  persist();
}
</script>

<style scoped>
.tp-provider-panel {
  margin-bottom: var(--tp-space-4);
}

.tp-provider-panel__head {
  margin-bottom: var(--tp-space-3);
}

.tp-provider-grid {
  display: grid;
  gap: var(--tp-space-3);
}

.tp-provider-card {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-lg);
  background: var(--tp-bg-surface);
  overflow: hidden;
}

.tp-provider-card--active {
  border-color: color-mix(in srgb, var(--tp-color-primary-600) 50%, var(--tp-border-default));
  box-shadow: var(--tp-shadow-sm);
}

.tp-provider-card__header {
  padding: var(--tp-space-4);
  border-bottom: 1px solid var(--tp-border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tp-provider-card__title {
  font-size: 16px;
  font-weight: 700;
}

.tp-provider-card__status {
  font-size: 12px;
  color: var(--tp-color-text-500);
  margin-top: 2px;
}

.tp-provider-card__body {
  padding: var(--tp-space-4);
  display: grid;
  gap: var(--tp-space-3);
}

.tp-provider-field {
  display: grid;
  gap: 8px;
  font-size: 12px;
  color: var(--tp-color-text-600);
}

.tp-provider-input {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-sm);
  background: var(--tp-bg-page);
  color: var(--tp-color-text-900);
  padding: 8px 10px;
}

.tp-model-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.tp-model-chip {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  background: var(--tp-bg-page);
  color: var(--tp-color-text-900);
  cursor: pointer;
  padding: 10px;
  text-align: left;
}

.tp-model-chip--active {
  border-color: color-mix(in srgb, var(--tp-color-primary-600) 60%, var(--tp-border-default));
  background: color-mix(in srgb, var(--tp-color-primary-600) 10%, var(--tp-bg-page));
}

.tp-model-chip__name {
  display: block;
  font-size: 12px;
  font-weight: 700;
}

.tp-model-chip__desc {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--tp-color-text-500);
}

.tp-provider-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.tp-provider-switch__track {
  width: 44px;
  height: 24px;
  border-radius: 9999px;
  background: var(--tp-border-strong);
  position: relative;
  transition: all 0.2s ease;
}

.tp-provider-switch__dot {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  transition: transform 0.2s ease;
}

input:checked + .tp-provider-switch__track {
  background: var(--tp-color-primary-600);
}

input:checked + .tp-provider-switch__track .tp-provider-switch__dot {
  transform: translateX(20px);
}
</style>
