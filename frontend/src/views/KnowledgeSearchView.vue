<template>
  <section class="tp-knowledge-search-page">
    <div v-if="searchError" class="tp-mb-3">
      <BaseState variant="error" :title="t('common.status.error')" :message="searchError" />
    </div>

    <div class="tp-surface tp-p-3 tp-mb-3">
      <form class="tp-row tp-g-3 tp-align-end" @submit.prevent="handleSearch">
        <div class="tp-col-12 tp-col-lg-8">
          <label class="tp-form-label">{{ t('knowledge.filters.keywordLabel') }}</label>
          <input
            v-model.trim="keyword"
            class="tp-input"
            type="search"
            :placeholder="t('knowledge.filters.keywordPlaceholder')"
          />
        </div>
        <div class="tp-col-12 tp-col-lg-2">
          <label class="tp-form-label">{{ t('knowledge.searchPage.threshold') }}</label>
          <input v-model.number="scoreThreshold" class="tp-input" type="number" min="0" max="1" step="0.05" />
        </div>
        <div class="tp-col-12 tp-col-lg-2 tp-grid">
          <TpButton
            type="submit"
            :loading="searchLoading"
            :disabled="searchLoading || !keyword"
            @click="handleSearch"
          >
            {{ t('knowledge.actions.search') }}
          </TpButton>
        </div>
      </form>
    </div>

    <div class="tp-surface tp-p-3">
      <div class="tp-flex tp-justify-between tp-align-center tp-gap-2 tp-mb-3">
        <div>
          <div class="tp-card__title">{{ t('knowledge.result.title') }}</div>
          <div class="tp-card__subtitle">{{ keyword || t('knowledge.result.empty') }}</div>
        </div>
        <TpTag variant="neutral">{{ pagination.total || 0 }}</TpTag>
      </div>

      <BaseState
        v-if="searchLoading"
        variant="loading"
        :title="t('knowledge.result.loading')"
      />
      <BaseState
        v-else-if="!keyword || !results.length"
        variant="empty"
        :title="t('knowledge.result.empty')"
      />
      <div v-else class="tp-result-list">
        <div
          v-for="item in results"
          :key="searchResultKey(item)"
          class="tp-result-item"
        >
          <div class="tp-flex tp-justify-between tp-gap-3">
            <div>
              <div class="tp-data-title">{{ item.file_name || '-' }}</div>
              <div class="tp-data-subtitle">{{ t('knowledge.result.source') }}: {{ item.source || '-' }}</div>
            </div>
            <div class="tp-text-end">
              <TpTag variant="info">{{ t('knowledge.result.score') }}: {{ formatScore(item.score) }}</TpTag>
              <div class="tp-small tp-mt-1" style="color: var(--tp-color-text-500)">{{ item.relevance || '-' }}</div>
            </div>
          </div>
          <div class="tp-mt-3 tp-small" style="color: var(--tp-color-text-500)">{{ item.content }}</div>
          <div class="tp-mt-3 tp-flex tp-justify-end">
            <TpButton
              v-if="item.file_id"
              variant="secondary"
              size="sm"
              @click="openInFiles(Number(item.file_id))"
            >
              {{ t('knowledge.searchPage.openInFiles') }}
            </TpButton>
          </div>
        </div>
      </div>

      <div class="tp-mt-3">
        <TpPager
          v-if="pagination.pages > 1"
          :page="pagination.page"
          :per-page="pagination.per_page"
          :total="pagination.total"
          :pages="pagination.pages"
          :has-prev="Boolean(pagination.has_prev)"
          :has-next="Boolean(pagination.has_next)"
          :loading="searchLoading"
          :previous-text="t('common.actions.previous')"
          :next-text="t('common.actions.next')"
          @change="changePage"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { searchKnowledge, type KnowledgePagination, type KnowledgeSearchResult } from '@/api/knowledge';

const { t } = useI18n();
const router = useRouter();

const keyword = ref('');
const scoreThreshold = ref(0.3);
const searchLoading = ref(false);
const searchError = ref('');
const results = ref<KnowledgeSearchResult[]>([]);
const pagination = ref<KnowledgePagination>({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

function formatScore(score?: number) {
  if (score === undefined || score === null || Number.isNaN(score)) return '-';
  return score.toFixed(3);
}

function searchResultKey(item: KnowledgeSearchResult) {
  return `${item.file_id ?? 'unknown'}-${item.source ?? 'result'}-${item.score ?? '0'}`;
}

async function runSearch(page = pagination.value.page) {
  if (!keyword.value) return;
  searchLoading.value = true;
  searchError.value = '';
  try {
    const requestPayload = {
      query: keyword.value,
      score_threshold: scoreThreshold.value,
      top_k: Math.max(page * pagination.value.per_page, 30),
      page,
      per_page: pagination.value.per_page
    };
    let response = await searchKnowledge(requestPayload);

    // 兜底：严格阈值下无结果时自动放宽一次，减少“明明有内容却搜不到”的体感
    if ((!response.documents || response.documents.length === 0) && scoreThreshold.value > 0.1) {
      response = await searchKnowledge({
        ...requestPayload,
        score_threshold: 0.1
      });
    }

    results.value = response.documents;
    pagination.value = response.pagination;
  } catch (error) {
    searchError.value = error instanceof Error ? error.message : t('knowledge.message.searchFailed');
    results.value = [];
  } finally {
    searchLoading.value = false;
  }
}

async function handleSearch() {
  pagination.value.page = 1;
  await runSearch(1);
}

async function changePage(page: number) {
  if (page < 1 || page > (pagination.value.pages || 1)) return;
  pagination.value.page = page;
  await runSearch(page);
}

function openInFiles(fileId: number) {
  if (!fileId) return;
  void router.push({ path: '/knowledge/files', query: { previewId: String(fileId) } });
}
</script>

<style scoped>
.tp-result-item {
  cursor: default;
}
</style>

