<template>
  <section :class="pageRootMarkedClass(pageMarkerKnowledgeSearch)">
    <KnowledgeVectorDisabledState v-if="vectorDisabled" class="mb-4" />
    <PagePanel
      v-else
      :title="t('knowledge.tabs.search')"
      :subtitle="t('knowledge.filters.keywordPlaceholder')"
    >
      <form :class="grid12ItemsEndClass" novalidate @submit.prevent="handleSearch">
        <div :class="colSpan12Lg8">
          <TpInput
            v-model="keyword"
            type="search"
            :label="t('knowledge.filters.keywordLabel')"
            :placeholder="t('knowledge.filters.keywordPlaceholder')"
            :disabled="vectorDisabled"
          />
        </div>
        <div :class="colSpan12Lg2">
          <TpInput
            v-model="scoreThreshold"
            type="number"
            :label="t('knowledge.searchPage.threshold')"
            :disabled="vectorDisabled"
            min="0"
            max="1"
            step="0.05"
          />
        </div>
        <div :class="[colSpan12Lg2, 'grid']">
          <TpButton
            type="submit"
            :loading="searchLoading"
            :disabled="vectorDisabled || searchLoading || !keyword"
          >
            {{ t('knowledge.actions.search') }}
          </TpButton>
        </div>
      </form>
    </PagePanel>

    <PagePanel v-if="!vectorDisabled" class="mt-4">
      <template #header>
        <div class="flex w-full items-center justify-between gap-2">
          <div>
            <div :class="panelTitleClass">{{ t('knowledge.result.title') }}</div>
            <div :class="panelSubtitleClass">{{ keyword || t('knowledge.result.empty') }}</div>
          </div>
          <TpTag variant="neutral">{{ pagination.total || 0 }}</TpTag>
        </div>
      </template>

      <BaseState
        v-if="searchError"
        variant="error"
        :title="t('common.status.error')"
        :message="searchError"
        class="mb-4"
      />
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
      <div v-else :class="resultListClass">
        <div
          v-for="item in results"
          :key="searchResultKey(item)"
          :class="[resultItemClass, 'cursor-default']"
        >
          <div class="flex justify-between gap-4">
            <div>
              <div :class="dataTitleClass">{{ item.file_name || '-' }}</div>
              <div :class="dataSubtitleClass">{{ t('knowledge.result.source') }}: {{ item.source || '-' }}</div>
            </div>
            <div class="text-right">
              <TpTag variant="info">{{ t('knowledge.result.score') }}: {{ formatScore(item.score) }}</TpTag>
              <div :class="[captionTextClass, 'mt-1 text-[var(--tp-color-text-500)]']">
                {{ t('knowledge.result.relevance') }}: {{ item.relevance || '-' }}
              </div>
            </div>
          </div>
          <div :class="[captionTextClass, 'mt-4 text-[var(--tp-color-text-500)]']">
            {{ t('knowledge.result.snippet') }}: {{ item.content }}
          </div>
          <div class="mt-4 flex justify-end">
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

      <div class="mt-4">
        <ListTablePager
          :pagination="pagination"
          :loading="searchPaging"
          :show-summary="true"
          @change="changePage"
        />
      </div>
    </PagePanel>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { type ListFetchMode } from '@/lib/list-fetch-mode';
import { useListPageChange } from '@/composables/useListPageChange';
import { useListTableLoading } from '@/composables/useListTableLoading';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import BaseState from '@/components/common/BaseState.vue';
import KnowledgeVectorDisabledState from '@/components/knowledge/KnowledgeVectorDisabledState.vue';
import PagePanel from '@/components/common/PagePanel.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import {
  colSpan12Lg2,
  colSpan12Lg8,
  grid12ItemsEndClass,
  pageMarkerKnowledgeSearch,
  pageRootMarkedClass
} from '@/lib/page-layout-ui';
import {
  captionTextClass,
  dataSubtitleClass,
  dataTitleClass,
  resultItemClass,
  resultListClass
} from '@/lib/page-typography';
import { panelSubtitleClass, panelTitleClass } from '@/lib/panel-ui';
import { cn } from '@/lib/utils';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import ListTablePager from '@/components/common/ListTablePager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import { useKnowledgeVectorGate } from '@/composables/useKnowledgeVectorNotice';
import { searchKnowledge, type KnowledgePagination, type KnowledgeSearchResult } from '@/api/knowledge';

const { t } = useI18n();
const router = useRouter();
const { vectorDisabled } = useKnowledgeVectorGate();

const keyword = ref('');
const scoreThreshold = ref(0.3);
const searchPaging = ref(false);
const results = ref<KnowledgeSearchResult[]>([]);
const { listLoading: searchLoading, listError: searchError, beginLoad, endLoad, failLoad } =
  useListTableLoading(results);
const pagination = ref<KnowledgePagination>({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

let searchSeq = 0;

function searchResultKey(item: KnowledgeSearchResult) {
  return `${item.file_id ?? item.file_name}-${item.chunk_index ?? item.content?.slice(0, 32)}`;
}

function formatScore(score?: number) {
  if (score == null || Number.isNaN(score)) return '-';
  return score.toFixed(3);
}

async function runSearch(page: number, mode: ListFetchMode = 'filter', options: { pager?: boolean } = {}) {
  if (vectorDisabled.value) return;
  const seq = ++searchSeq;
  searchPaging.value = mode === 'page' && options.pager !== false;
  beginLoad(mode);
  try {
    const requestPayload = {
      query: keyword.value.trim(),
      score_threshold: scoreThreshold.value,
      page,
      per_page: pagination.value.per_page
    };
    const response = await searchKnowledge(requestPayload);
    if (seq !== searchSeq) return;

    results.value = response.documents;
    pagination.value = response.pagination;
  } catch (error) {
    if (seq !== searchSeq) return;
    failLoad(getUserFacingErrorMessage(error, t('knowledge.message.searchFailed')), () => {
      results.value = [];
    });
  } finally {
    if (seq === searchSeq) {
      endLoad();
      searchPaging.value = false;
    }
  }
}

async function handleSearch() {
  if (vectorDisabled.value) return;
  keyword.value = keyword.value.trim();
  pagination.value.page = 1;
  const mode: ListFetchMode = results.value.length > 0 ? 'page' : 'filter';
  await runSearch(1, mode, { pager: false });
}

const { changePage } = useListPageChange(
  pagination,
  (page, mode) => runSearch(page, mode),
  { onAcceptPage: (page) => { pagination.value.page = page; } }
);

function openInFiles(fileId: number) {
  if (!fileId) return;
  void router.push({ path: '/knowledge/files', query: { previewId: String(fileId) } });
}
</script>
