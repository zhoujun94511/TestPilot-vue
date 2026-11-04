<template>
  <TpCard :class="aiResultCardClass" :title="title" :subtitle="subtitle">
    <template #header>
      <div :class="aiResultHeadClass">
        <div>
          <div :class="aiResultTitleClass">{{ title }}</div>
          <div v-if="subtitle" :class="aiResultSubtitleClass">{{ subtitle }}</div>
        </div>
        <div :class="aiResultMetaClass">
          <TpTag v-if="confidenceLabel" variant="ai">{{ confidenceLabel }}</TpTag>
          <TpTag v-if="riskLabel" :variant="riskTagVariant">{{ riskLabel }}</TpTag>
        </div>
      </div>
    </template>

    <div :class="aiResultSectionClass">
      <div :class="aiResultSectionTitleClass">{{ t('ai.summary') }}</div>
      <slot name="summary" />
    </div>

    <div :class="aiResultSectionClass">
      <div :class="aiResultSectionTitleClass">{{ t('ai.metrics') }}</div>
      <slot name="metrics">
        <TpProgress v-if="typeof confidence === 'number'" :value="confidence" :label="confidenceTextLabel" />
      </slot>
    </div>

    <div v-if="$slots.risk || riskText" :class="aiResultSectionClass">
      <div :class="aiResultSectionTitleClass">{{ t('ai.risk') }}</div>
      <div :class="riskBlockPanelClass({ tone: riskPanelTone })">
        <div :class="riskBlockTitleClass">{{ riskTitleLabel }}</div>
        <div :class="riskBlockTextClass">
          <slot name="risk">{{ riskText }}</slot>
        </div>
      </div>
    </div>

    <div :class="aiResultSectionClass">
      <button type="button" :class="aiResultCollapseToggleClass" @click="toggleEvidence">
        <span>{{ evidenceOpen ? t('ai.hideEvidence') : t('ai.showEvidence') }}</span>
      </button>
      <div v-if="evidenceOpen" :class="aiResultCollapseContentClass">
        <div :class="aiResultSectionTitleClass">{{ t('ai.evidence') }}</div>
        <slot name="evidence" />
      </div>
    </div>

    <div :class="aiResultCollapseSectionClass">
      <button type="button" :class="aiResultCollapseToggleClass" @click="toggleRaw">
        <span>{{ rawOpen ? t('ai.hideRaw') : t('ai.showRaw') }}</span>
      </button>
      <div v-if="rawOpen" :class="aiResultCollapseContentClass">
        <div :class="aiResultSectionTitleClass">{{ t('ai.raw') }}</div>
        <slot name="raw" />
      </div>
    </div>
  </TpCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  aiResultCardClass,
  aiResultCollapseContentClass,
  aiResultCollapseSectionClass,
  aiResultCollapseToggleClass,
  aiResultHeadClass,
  aiResultMetaClass,
  aiResultSectionClass,
  aiResultSectionTitleClass,
  aiResultSubtitleClass,
  aiResultTitleClass
} from '@/lib/ai-result-ui';
import {
  riskBlockPanelClass,
  riskBlockTextClass,
  riskBlockTitleClass,
  type RiskBlockPanelTone
} from '@/lib/notice-ui';
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

const riskPanelTone = computed((): RiskBlockPanelTone => {
  if (props.riskLevel === 'danger') return 'danger';
  if (props.riskLevel === 'info') return 'info';
  return 'warning';
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
