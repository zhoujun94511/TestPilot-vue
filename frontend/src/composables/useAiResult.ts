import { computed, unref, type MaybeRefOrGetter } from 'vue';
import { useI18n } from 'vue-i18n';

export interface AiResultLike {
  confidence?: number | null;
  score?: number | null;
  reliability_score?: number | null;
  processing_rate?: number | string | null;
  hallucination_detection?: {
    score?: number | null;
    quality_score?: number | null;
    avg_confidence?: number | null;
  } | null;
  summary?: {
    total_count?: number | null;
  } | null;
  tokens_used?: number | null;
  total?: number | null;
  total_cases?: number | null;
}

export interface AiResultSnapshot {
  confidence: number;
  riskLevel: 'info' | 'warning' | 'danger';
  riskLabel: string;
  riskTitle: string;
  confidenceLabel: string;
}

function clampConfidence(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function resolveAiResultSnapshot(source: AiResultLike | null | undefined, t: (key: string, args?: Record<string, unknown>) => string): AiResultSnapshot {
  const detection = source?.hallucination_detection;
  const scaledDetectionScore = [detection?.quality_score, detection?.avg_confidence]
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
    .map((value) => (value <= 1 ? value * 100 : value));
  const directCandidates = [
    source?.confidence,
    source?.hallucination_detection?.score,
    ...scaledDetectionScore,
    source?.reliability_score,
    source?.score
  ].map((value) => Number(value)).filter((value) => Number.isFinite(value));

  let confidence = directCandidates.length ? clampConfidence(directCandidates[0]) : NaN;

  if (!Number.isFinite(confidence) && source?.processing_rate !== undefined && source?.processing_rate !== null && source?.processing_rate !== '') {
    const rate = Number(source.processing_rate);
    if (Number.isFinite(rate)) {
      confidence = clampConfidence(rate > 100 ? rate / 100 : rate);
    }
  }

  if (!Number.isFinite(confidence)) {
    const count = Number(source?.summary?.total_count ?? source?.total ?? source?.total_cases ?? 0);
    if (count > 0) {
      confidence = clampConfidence(55 + count * 6 + (Number(source?.tokens_used ?? 0) > 0 ? 5 : 0));
    }
  }

  if (!Number.isFinite(confidence)) confidence = 0;

  let riskLevel: AiResultSnapshot['riskLevel'] = 'info';
  if (confidence < 60) riskLevel = 'danger';
  else if (confidence < 80) riskLevel = 'warning';

  const riskLabel = riskLevel === 'danger'
    ? t('ai.highRisk')
    : riskLevel === 'warning'
      ? t('ai.reviewSuggested')
      : t('ai.stable');

  const riskTitle = riskLevel === 'danger'
    ? t('ai.hallucinationDetected')
    : riskLevel === 'warning'
      ? t('ai.manualReview')
      : t('ai.systemConfidenceStable');

  return {
    confidence,
    riskLevel,
    riskLabel,
    riskTitle,
    confidenceLabel: `${t('ai.derivedConfidence')} ${confidence}%`
  };
}

export function useAiResult(source: MaybeRefOrGetter<AiResultLike | null | undefined>) {
  const { t } = useI18n();

  return computed(() => resolveAiResultSnapshot(unref(source), t));
}
