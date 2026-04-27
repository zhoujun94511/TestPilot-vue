<template>
  <TpCard class="tp-ai-card" :title="title" :subtitle="subtitle">
    <template #header>
      <div class="tp-ai-card__head">
        <div>
          <div class="tp-ai-card__title">{{ title }}</div>
          <div v-if="subtitle" class="tp-ai-card__subtitle">{{ subtitle }}</div>
        </div>
        <div class="tp-ai-card__meta">
          <TpTag v-if="confidenceLabel" variant="ai">{{ confidenceLabel }}</TpTag>
          <TpTag v-if="riskLabel" :variant="riskTagVariant">{{ riskLabel }}</TpTag>
        </div>
      </div>
    </template>

    <div class="tp-ai-card__section">
      <div class="tp-ai-card__section-title">{{ t('ai.summary') }}</div>
      <slot name="summary" />
    </div>

    <div class="tp-ai-card__section">
      <div class="tp-ai-card__section-title">{{ t('ai.metrics') }}</div>
      <slot name="metrics">
        <TpProgress v-if="typeof confidence === 'number'" :value="confidence" :label="confidenceTextLabel" />
      </slot>
    </div>

    <div v-if="$slots.risk || riskText" class="tp-ai-card__section">
      <div class="tp-ai-card__section-title">{{ t('ai.risk') }}</div>
      <div class="tp-risk-block" :class="riskBlockClass">
        <div class="tp-risk-block__title">{{ riskTitleLabel }}</div>
        <div class="tp-risk-block__text">
          <slot name="risk">{{ riskText }}</slot>
        </div>
      </div>
    </div>

    <div class="tp-ai-card__section">
      <button type="button" class="tp-collapse__toggle" @click="toggleEvidence">
        <span>{{ evidenceOpen ? t('ai.hideEvidence') : t('ai.showEvidence') }}</span>
      </button>
      <div v-if="evidenceOpen" class="tp-collapse__content">
        <div class="tp-ai-card__section-title">{{ t('ai.evidence') }}</div>
        <slot name="evidence" />
      </div>
    </div>

    <div class="tp-ai-card__section tp-collapse">
      <button type="button" class="tp-collapse__toggle" @click="toggleRaw">
        <span>{{ rawOpen ? t('ai.hideRaw') : t('ai.showRaw') }}</span>
      </button>
      <div v-if="rawOpen" class="tp-collapse__content">
        <div class="tp-ai-card__section-title">{{ t('ai.raw') }}</div>
        <slot name="raw" />
      </div>
    </div>
  </TpCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import TpCard from './base/TpCard.vue';
import TpProgress from './base/TpProgress.vue';
import TpTag from './base/TpTag.vue';

const { t } = useI18n();

const props = withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  confidence?: number;
  confidenceLabel?: string;
  confidenceText?: string;
  riskLabel?: string;
  riskText?: string;
  riskTitle?: string;
  riskLevel?: 'warning' | 'danger' | 'info';
}>(), {
  confidenceText: '',
  riskTitle: '',
  riskLevel: 'warning'
});

const evidenceOpen = ref(true);
const rawOpen = ref(false);

const riskTagVariant = computed(() => {
  if (props.riskLevel === 'danger') return 'danger';
  if (props.riskLevel === 'info') return 'info';
  return 'warning';
});

const riskBlockClass = computed(() => {
  if (props.riskLevel === 'danger') return 'tp-risk-block--danger';
  if (props.riskLevel === 'info') return 'tp-risk-block--info';
  return '';
});

const confidenceTextLabel = computed(() => props.confidenceText || t('ai.confidence'));
const riskTitleLabel = computed(() => props.riskTitle || t('ai.hallucinationDetected'));


function toggleEvidence() {
  evidenceOpen.value = !evidenceOpen.value;
}

function toggleRaw() {
  rawOpen.value = !rawOpen.value;
}
</script>
