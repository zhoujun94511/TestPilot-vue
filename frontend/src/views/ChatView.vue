<template>
  <section :class="pageFluidShellMarkedClass(pageMarkerChat)">
    <ActionBar>
      <template v-if="showChatToolbarHint" #lead>
        <p :class="pageToolbarSubtitleClass">{{ chatToolbarHintText }}</p>
      </template>
      <template #actions>
        <TpButton variant="ghost" size="sm" :disabled="sessionLoading || sendLoading" @click="handleNewSession">
          {{ t('chat.actions.newSession') }}
        </TpButton>
        <TpButton
          variant="ghost"
          size="sm"
          :loading="sessionLoading"
          :disabled="sessionLoading || !currentSessionId"
          @click="refreshCurrentSession"
        >
          {{ t('chat.actions.refresh') }}
        </TpButton>
        <TpButton
          variant="ghost"
          size="sm"
          :loading="exportLoading"
          :disabled="!currentSessionId"
          :aria-label="exportLoading ? t('chat.actions.exporting') : undefined"
          @click="handleExport"
        >
          {{ t('chat.actions.export') }}
        </TpButton>
        <TpButton
          variant="danger"
          size="sm"
          :disabled="sendLoading || !canClearConversation"
          @click="handleClearCurrentSession"
        >
          {{ t('chat.actions.clearSession') }}
        </TpButton>
      </template>
    </ActionBar>

    <PageNoticeBanner
      :notice="chatBanner"
      @close="clearChatBanner"
    />

    <div :class="grid12StretchClass">
      <aside :class="colSpan12Xl3">
        <TpCard>
          <template #header>
            <div>
              <div :class="sectionTitleClass">{{ t('chat.sessions.title') }}</div>
              <div :class="sectionSubtitleClass">{{ t('chat.sessions.count', { count: sessionTotalCount }) }}</div>
            </div>
          </template>

          <BaseState
            v-if="sessionLoading && !sessions.length"
            variant="loading"
            :title="t('chat.state.loadingSessions')"
          />
          <BaseState
            v-else-if="sessionError"
            variant="error"
            :title="t('common.status.error')"
            :message="sessionError"
            :retry-text="t('common.actions.retry')"
            @retry="loadSessions"
          />
          <BaseState
            v-else-if="!sessions.length"
            variant="empty"
            :title="t('chat.sessions.emptyTitle')"
            :message="t('chat.sessions.emptyMessage')"
          >
            <TpButton
              class="mt-3"
              variant="primary"
              size="sm"
              :disabled="sessionLoading || sendLoading"
              @click="handleNewSession"
            >
              {{ t('chat.actions.newSession') }}
            </TpButton>
          </BaseState>
          <div v-else :class="chatSessionListClass">
            <div
              v-for="session in sessions"
              :key="session.session_id"
              :class="chatSessionItemClass({ active: session.session_id === currentSessionId })"
              @click="selectSession(session.session_id)"
            >
              <div :class="chatSessionMainClass">
                <TpInput
                  v-if="renamingSessionId === session.session_id"
                  v-model="renameDraft"
                  bare
                  :disabled="sessionLoading || sendLoading"
                  @click.stop
                  @keydown.enter.stop.prevent="submitRename(session.session_id)"
                  @keydown.esc.stop.prevent="cancelRename"
                />
                <TpTruncateText
                  v-else
                  :text="displaySessionTitle(session.title)"
                  :class="dataTitleClass"
                />
                <TpTruncateText
                  :text="sessionPreview(session)"
                  :class="chatMessageMetaClass"
                />
              </div>
              <div :class="chatSessionActionsClass">
                <TpTag variant="neutral">{{ session.message_count ?? 0 }}</TpTag>
                <TpButton
                  v-if="renamingSessionId === session.session_id"
                  variant="ghost"
                  size="sm"
                  :disabled="sessionLoading || sendLoading"
                  @click.stop="submitRename(session.session_id)"
                >
                  {{ t('common.actions.save') }}
                </TpButton>
                <TpButton
                  v-else
                  variant="ghost"
                  size="sm"
                  :disabled="sessionLoading || sendLoading"
                  @click.stop="startRename(session)"
                >
                  {{ t('chat.actions.renameSession') }}
                </TpButton>
                <TpButton
                  variant="ghost"
                  size="sm"
                  :class="chatSessionDeleteBtnClass"
                  :disabled="sessionLoading || sendLoading"
                  @click.stop="handleDeleteSession(session.session_id)"
                >
                  {{ t('chat.actions.deleteSession') }}
                </TpButton>
              </div>
            </div>
            <TpPager
              class="pt-1"
              :page="sessionPagination.page"
              :per-page="sessionPagination.per_page"
              :total="sessionPagination.total"
              :pages="sessionPagination.pages"
              :has-prev="Boolean(sessionPagination.has_prev)"
              :has-next="Boolean(sessionPagination.has_next)"
              :loading="sessionLoading"
              :previous-text="t('common.actions.previous')"
              :next-text="t('common.actions.next')"
              @change="changeSessionPage"
            />
          </div>
        </TpCard>
      </aside>

      <section :class="colSpan12Xl9">
        <TpCard :class="chatMainCardClass">
          <template #header>
            <div :class="chatMainCardHeaderClass">
              <div>
                <div :class="sectionTitleClass">{{ mainCardTitle }}</div>
                <div :class="sectionSubtitleClass">
                  <span v-if="currentSessionId">{{ t('chat.sessions.currentId') }}</span>
                  <span v-else>{{ t('chat.sessions.noSessionSelected') }}</span>
                </div>
              </div>
              <TpTag v-if="currentSessionId" variant="neutral">
                <span v-if="historyLoading">{{ t('chat.state.loadingHistory') }}</span>
                <span v-else>{{ messageCountLabel }}</span>
              </TpTag>
            </div>
          </template>

          <div ref="messagePanelRef" :class="chatMessagePanelClass" @scroll="handleMessagePanelScroll">
            <BaseState
              v-if="historyLoading"
              variant="loading"
              :title="t('chat.state.loadingHistory')"
            />
            <BaseState
              v-else-if="historyError"
              variant="error"
              :title="t('common.status.error')"
              :message="historyError"
              :retry-text="t('common.actions.retry')"
              @retry="reloadCurrentHistory"
            />
            <BaseState
              v-else-if="!messages.length"
              variant="empty"
              :title="t('chat.state.emptyTitle')"
              :message="t('chat.state.emptyMessage')"
            >
              <div :class="chatEmptyStateClass">
                <ChatAssistantAvatar size="sm" decorative class="mx-auto mb-3" />
                <p class="mb-0">{{ t('chat.state.welcomeLead') }}</p>
                <p class="mb-0 mt-1">{{ t('chat.state.welcomePrompt') }}</p>
                <ul :class="chatEmptyListClass">
                  <li v-for="(question, index) in emptyStarterQuestions" :key="`empty-starter-${index}`">
                    <button
                      type="button"
                      :class="chatEmptyQuestionClass"
                      :disabled="sendLoading"
                      @click="draftMessage = question"
                    >
                      {{ question }}
                    </button>
                  </li>
                </ul>
              </div>
            </BaseState>
            <div v-if="messages.length" :class="[captionTextClass, chatMetaClass, 'mb-2']">
              {{ t('chat.history.title') }}
            </div>
            <div v-if="messages.length" :class="chatMessageListClass">
              <div
                v-for="message in messages"
                :key="message.key"
                :class="cn(chatMessageRowClass(message.role), message.role === 'user' && 'items-start')"
              >
                <template v-if="message.role === 'user'">
                  <div :class="cn(chatMessageColumnClass, 'items-end')">
                    <div :class="chatUserBubbleClass">
                      <ChatMessageContent
                        :content="message.content || t('chat.state.emptyMessage')"
                        :role="message.role"
                      />
                    </div>
                    <div :class="chatMessageFootMetaClass">
                      {{ formatMessageFootMeta(message) }}
                    </div>
                  </div>
                  <ChatUserAvatar size="xs" decorative :class="chatUserAvatarClass" />
                </template>

                <div v-else-if="message.role === 'system'" :class="cn(chatAssistantColumnClass, 'w-full')">
                  <div :class="chatAssistantBubbleSystemClass">
                    <ChatMessageContent
                      :content="message.content || t('chat.state.emptyMessage')"
                      :role="message.role"
                    />
                  </div>
                  <div :class="chatMessageFootMetaClass">
                    {{ formatMessageFootMeta(message) }}
                  </div>
                </div>

                <template v-else>
                  <ChatAssistantAvatar size="xs" decorative :class="chatAssistantAvatarClass" />
                  <div :class="chatAssistantColumnClass">
                    <div :class="chatAssistantBubbleClass">
                      <ChatMessageContent
                        :content="message.content || t('chat.state.emptyMessage')"
                        :role="message.role"
                      />
                    </div>
                    <div :class="chatMessageFootMetaClass">
                      {{ formatMessageFootMeta(message) }}
                    </div>
                  </div>
                </template>
              </div>
            </div>
            <TpButton
              v-if="showJumpToLatest"
              :class="chatJumpLatestButtonClass"
              variant="secondary"
              size="sm"
              @click="jumpToLatest"
            >
              {{ t('chat.actions.jumpToLatest', { count: unreadCount }) }}
            </TpButton>
          </div>

          <TpPager
            v-if="messages.length && !historyLoading && !historyError"
            :class="chatHistoryPagerClass"
            :page="historyPagination.page"
            :per-page="historyPagination.per_page"
            :total="historyPagination.total"
            :pages="historyPagination.pages"
            :has-prev="Boolean(historyPagination.has_prev)"
            :has-next="Boolean(historyPagination.has_next)"
            :loading="historyLoading"
            :previous-text="t('common.actions.previous')"
            :next-text="t('common.actions.next')"
            @change="changeHistoryPage"
          />

          <div v-if="suggestedQuestions.length" :class="chatSuggestionsClass">
            <div :class="chatSuggestionsHeaderClass">
              <span>{{ t('chat.quickReply.title') }}</span>
              <span :class="[captionTextClass, chatMetaClass]">
                {{ quickReplyStatsLine }}
              </span>
            </div>
            <div :class="chatSuggestionsActionsClass">
              <TpButton
                v-for="(suggestion, index) in suggestedQuestions"
                :key="`suggestion-${index}-${suggestion}`"
                variant="secondary"
                size="sm"
                :disabled="sendLoading"
                @click="handleSuggestionClick(suggestion, $event)"
              >
                {{ suggestion }}
              </TpButton>
            </div>
          </div>

          <form :class="chatComposerShellClass" novalidate @submit.prevent="handleSend()">
            <label :class="formLabelClass">{{ t('chat.composer.label') }}</label>
            <div v-if="templatePanelEnabled" :class="chatTemplatePanelClass">
              <div :class="[sectionTitleClass, 'mb-2']">{{ t('chat.template.title') }}</div>
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div :class="[captionTextClass, chatMetaClass]">{{ t('chat.template.selectLabel') }}</div>
                <div :class="pageToolbarStripClass">
                  <select
                    v-model="selectedTemplateType"
                    :class="mergeControlSizeClass(selectCompactVariants(), chatTemplateSelectClass, 'min-w-[180px] max-w-full')"
                    :disabled="sendLoading"
                    @change="handleTemplateTypeChange"
                  >
                    <option v-for="item in templateOptions" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                  <TpButton
                    variant="ghost"
                    size="sm"
                    :disabled="sendLoading || templatePreviewLoading || !templatePreviewContent"
                    @click="handleInsertTemplate"
                  >
                    {{ t('chat.actions.insertTemplate') }}
                  </TpButton>
                </div>
              </div>
              <div :class="chatTemplatePreviewClass">
                <div v-if="templatePreviewLoading" :class="[captionTextClass, chatMetaClass]">{{ t('chat.template.loading') }}</div>
                <div v-else-if="templatePreviewContent" :class="captionTextClass">{{ templatePreviewContent }}</div>
                <div v-else :class="[captionTextClass, chatMetaClass]">{{ t('chat.template.empty') }}</div>
              </div>
            </div>
            <TpInput
              v-model="draftMessage"
              bare
              as="textarea"
              :rows="4"
              :placeholder="t('chat.composer.placeholder')"
              :disabled="sendLoading"
              @keydown.enter.exact.prevent="handleSend()"
            />
            <p :class="[captionTextClass, chatMetaClass, 'mt-2']">{{ t('chat.composer.hint') }}</p>

            <div :class="chatComposerFooterClass">
              <div :class="chatToggleGroupClass">
                <TpSwitch
                  v-model="streamEnabled"
                  switch-id="chatStreamEnabled"
                  :label="t('chat.composer.streamToggle')"
                />
                <TpSwitch
                  v-model="smartReplyEnabled"
                  switch-id="chatSmartReplyEnabled"
                  :label="t('chat.composer.smartReplyToggle')"
                />
                <TpSwitch
                  v-model="templatePanelEnabled"
                  switch-id="chatTemplatePanelEnabled"
                  :label="t('chat.composer.templateToggle')"
                />
              </div>
              <div :class="chatComposerActionsClass">
                <div :class="pageToolbarStripClass">
                  <TpButton
                    variant="ghost"
                    size="sm"
                    :disabled="sendLoading || !draftMessage.trim()"
                    @click="draftMessage = ''"
                  >
                    {{ t('common.actions.cancel') }}
                  </TpButton>
                  <TpButton
                    type="submit"
                    variant="primary"
                    size="sm"
                    :loading="sendLoading"
                    :disabled="!draftMessage.trim()"
                    :aria-label="sendLoading ? t('chat.actions.sending') : undefined"
                  >
                    {{ t('chat.actions.send') }}
                  </TpButton>
                </div>
              </div>
            </div>
          </form>
        </TpCard>
      </section>
    </div>

    <ConfirmDialog
      v-model="deleteConfirmVisible"
      :title="t('common.actions.delete')"
      :message="pendingDeleteSessionTitle
        ? t('chat.message.deleteSessionConfirm', { title: pendingDeleteSessionTitle })
        : ''"
      :confirm-text="t('common.actions.confirm')"
      :cancel-text="t('common.actions.cancel')"
      confirm-variant="danger"
      @confirm="confirmDeleteSession"
      @cancel="cancelDeleteSession"
    />
    <ConfirmDialog
      v-model="clearConfirmVisible"
      :title="t('chat.actions.clearSession')"
      :message="t('chat.message.clearSessionConfirm')"
      :confirm-text="t('common.actions.confirm')"
      :cancel-text="t('common.actions.cancel')"
      confirm-variant="danger"
      @confirm="confirmClearCurrentSession"
      @cancel="clearConfirmVisible = false"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import ActionBar from '@/components/common/ActionBar.vue';
import PageNoticeBanner from '@/components/common/PageNoticeBanner.vue';
import { useChatBooleanPreference } from '@/composables/useChatPreferences';
import {
  localizeModelStatusValue,
  localizeSessionTitle,
  stripLeadingToolMetaLines
} from '@/lib/chat-backend-copy';
import { formLabelClass } from '@/lib/field-control';
import { pageToolbarStripClass, pageToolbarSubtitleClass } from '@/lib/page-chrome-ui';
import { dataTitleClass, sectionSubtitleClass, sectionTitleClass } from '@/lib/page-typography';
import {
  colSpan12Xl3,
  colSpan12Xl9,
  grid12StretchClass,
  pageFluidShellMarkedClass,
  pageMarkerChat
} from '@/lib/page-layout-ui';
import {
  chatComposerActionsClass,
  chatComposerFooterClass,
  chatComposerShellClass,
  chatEmptyListClass,
  chatEmptyQuestionClass,
  chatEmptyStateClass,
  chatHistoryPagerClass,
  chatAssistantAvatarClass,
  chatAssistantBubbleClass,
  chatAssistantBubbleSystemClass,
  chatAssistantColumnClass,
  chatJumpLatestButtonClass,
  chatMainCardClass,
  chatMainCardHeaderClass,
  chatMessageColumnClass,
  chatMessageFootMetaClass,
  chatMessageListClass,
  chatMessageMetaClass,
  chatMessagePanelClass,
  chatMessageRowClass,
  chatUserBubbleClass,
  chatUserAvatarClass,
  chatMetaClass,
  chatSessionActionsClass,
  chatSessionListClass,
  chatSuggestionsActionsClass,
  chatSuggestionsClass,
  chatSuggestionsHeaderClass,
  chatSessionDeleteBtnClass,
  chatSessionItemClass,
  chatSessionMainClass,
  chatTemplatePanelClass,
  chatTemplatePreviewClass,
  chatTemplateSelectClass,
  chatToggleGroupClass
} from '@/lib/chat-ui';
import { captionTextClass } from '@/lib/page-typography';
import { mergeControlSizeClass, selectCompactVariants } from '@/lib/field-control';
import { cn } from '@/lib/utils';
import { formatDateTimeCompact } from '@/lib/format';
import { triggerBlobDownload } from '@/lib/download';
import { getUserFacingErrorMessage } from '@/lib/user-facing-error';
import { useChatAbort } from '@/composables/useChatAbort';
import { useChatHistory } from '@/composables/useChatHistory';
import { createChatSendHandler } from '@/composables/useChatSend';
import { useChatSessions } from '@/composables/useChatSessions';
import { usePendingExperimentalAction } from '@/composables/usePendingExperimentalAction';
import { usePageNotifier } from '@/composables/usePageNotifier';
import { useRouter } from 'vue-router';
import ChatAssistantAvatar from '@/components/brand/ChatAssistantAvatar.vue';
import ChatUserAvatar from '@/components/brand/ChatUserAvatar.vue';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import BaseState from '@/components/common/BaseState.vue';
import ChatMessageContentSkeleton from '@/components/chat/ChatMessageContentSkeleton.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpTruncateText from '@/components/ui/base/TpTruncateText.vue';
import TpInput from '@/components/ui/base/TpInput.vue';
import TpSwitch from '@/components/ui/base/TpSwitch.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  clearChatHistory,
  createChatSession,
  deleteChatSession,
  exportChatHistory,
  trackQuickReplyFeedback,
  updateChatSession,
  getChatConfig,
  getChatTemplate,
  getQuickReplyStats,
  type ChatMessageRecord,
  type ChatSessionRecord,
  type QuickReplyStats
} from '@/api/chat';
import { looksLikeGenerateCasesSuggestion } from '@/config/experimentalTools';

const ChatMessageContent = defineAsyncComponent({
  loader: () => import('@/components/chat/ChatMessageContent.vue'),
  loadingComponent: ChatMessageContentSkeleton,
  delay: 120,
  timeout: 10000
});

interface NoticeState {
  type: 'success' | 'danger' | 'warning' | 'info';
  message: string;
}

interface DisplayMessage {
  key: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_time?: string | null;
  pending?: boolean;
  tokens_used?: number;
  model_name?: string;
}

interface TemplateOption {
  value: string;
  label: string;
}

const { t, locale } = useI18n();
const router = useRouter();
const {
  banner: chatBanner,
  clearBanner: clearChatBanner,
  showNotice: notifyShowNotice
} = usePageNotifier();

const messages = ref<DisplayMessage[]>([]);
const currentSessionId = ref('');
const currentSessionTitle = ref('');
const draftMessage = ref('');
const { sendLoading, abortActiveChat, beginAbortableRequest, isAbortError } = useChatAbort();
const exportLoading = ref(false);
const chatConfig = ref<Awaited<ReturnType<typeof getChatConfig>> | null>(null);
const pendingAssistantKey = ref('');
const suggestedQuestions = ref<string[]>([]);
const quickReplyStats = ref<QuickReplyStats | null>(null);

const quickReplyStatsLine = computed(() => {
  const batch = t('chat.quickReply.statsHint', { count: suggestedQuestions.value.length });
  const stats = quickReplyStats.value;
  if (!stats) return batch;
  const clicks = Number(stats.total_clicks ?? 0);
  const users = Number(stats.total_users ?? 0);
  return `${batch} · ${t('chat.quickReply.statsGlobal', { clicks, users })}`;
});

async function refreshQuickReplyStats() {
  if (!smartReplyEnabled.value) return;
  try {
    quickReplyStats.value = await getQuickReplyStats();
  } catch {
    quickReplyStats.value = null;
  }
}
const streamEnabled = useChatBooleanPreference('streamEnabled', true);
const smartReplyEnabled = useChatBooleanPreference('smartReplyEnabled', true);
const templatePanelEnabled = useChatBooleanPreference('templatePanelEnabled', false);
const { resetPendingAction, restorePendingAction } = usePendingExperimentalAction();
const selectedTemplateType = ref('test_strategy');
const templatePreviewLoading = ref(false);
const templatePreviewContent = ref('');
const messageCounter = ref(0);
const messagePanelRef = ref<HTMLElement | null>(null);
const autoScrollEnabled = ref(true);
const forceFollowUntil = ref(0);
const showJumpToLatest = ref(false);
const unreadCount = ref(0);
const deleteConfirmVisible = ref(false);
const pendingDeleteSessionId = ref('');
const pendingDeleteSessionTitle = ref('');
const clearConfirmVisible = ref(false);

const sessionModelLabel = computed(() => localizeModelStatus(chatConfig.value?.default_model || t('chat.sessions.defaultTitle')));
const emptyStarterQuestions = computed(() => [
  t('chat.state.starters.caseDesignReview'),
  t('chat.state.starters.testStrategy'),
  t('chat.state.starters.defectAnalysis'),
  t('chat.state.starters.automation'),
  t('chat.state.starters.performance')
]);
const canClearConversation = computed(() =>
  messages.value.length > 0
  || suggestedQuestions.value.length > 0
  || draftMessage.value.trim().length > 0
);
const templateOptions = computed<TemplateOption[]>(() => [
  { value: 'test_strategy', label: t('chat.template.types.testStrategy') },
  { value: 'case_review', label: t('chat.template.types.caseReview') },
  { value: 'bug_analysis', label: t('chat.template.types.bugAnalysis') },
  { value: 'automation_advice', label: t('chat.template.types.automationAdvice') },
  { value: 'performance_test', label: t('chat.template.types.performanceTest') }
]);
function setNotice(type: NoticeState['type'], message: string) {
  notifyShowNotice(type, message);
}

const chatDateLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'));

function formatChatDateTime(value: string | null | undefined) {
  return formatDateTimeCompact(value, chatDateLocale.value, '');
}

function sessionPreview(session: ChatSessionRecord) {
  const preview = session.last_activity ? formatChatDateTime(session.last_activity) : '';
  return preview || t('chat.sessions.emptyPreview');
}

function resolveRoleLabel(role: string) {
  if (role === 'user') return t('chat.roles.user');
  if (role === 'assistant') return t('chat.roles.assistant');
  return t('chat.roles.system');
}

function formatMessageFootMeta(message: DisplayMessage) {
  const parts: string[] = [resolveRoleLabel(message.role)];
  if (message.created_time) {
    parts.push(formatChatDateTime(message.created_time));
  }
  if (message.role === 'assistant' && message.tokens_used) {
    parts.push(t('chat.metrics.tokens', { count: message.tokens_used }));
  }
  return parts.join(' · ');
}

function localizeModelStatus(value: string | null | undefined) {
  return localizeModelStatusValue(value, t);
}

function displaySessionTitle(raw: string | null | undefined) {
  return localizeSessionTitle(raw, t);
}

const mainCardTitle = computed(() => {
  if (!currentSessionId.value) {
    return t('chat.page.title');
  }
  return displaySessionTitle(currentSessionTitle.value);
});

function normalizeMessages(records: ChatMessageRecord[]): DisplayMessage[] {
  return records.map((item, index) => ({
    key: `${item.id ?? index}-${index}`,
    role: item.role === 'system' ? 'system' : item.role === 'user' ? 'user' : 'assistant',
    content: normalizeDisplayContent(item.content, item.role === 'system' ? 'system' : item.role === 'user' ? 'user' : 'assistant'),
    created_time: item.created_time,
    tokens_used: item.tokens_used,
    model_name: item.model_name
  }));
}

function normalizeDisplayContent(content: string, role: DisplayMessage['role']): string {
  const raw = String(content || '').trim();
  if (!raw || role === 'user') return raw;
  return stripLeadingToolMetaLines(raw);
}

function resetConversation() {
  messages.value = [];
  suggestedQuestions.value = [];
  draftMessage.value = '';
  pendingAssistantKey.value = '';
  messageCounter.value = 0;
  resetPendingAction();
}

function scrollMessagesToBottom(smooth = false) {
  const panel = messagePanelRef.value;
  if (!panel) return;
  panel.scrollTo({
    top: panel.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto'
  });
  autoScrollEnabled.value = true;
  showJumpToLatest.value = false;
}

function enableForceFollow(durationMs = 3000) {
  forceFollowUntil.value = Date.now() + Math.max(0, durationMs);
}

function isForceFollowActive() {
  return Date.now() <= forceFollowUntil.value;
}

function isNearBottom(threshold = 80) {
  const panel = messagePanelRef.value;
  if (!panel) return true;
  return panel.scrollHeight - panel.scrollTop - panel.clientHeight <= threshold;
}

function handleMessagePanelScroll() {
  const nearBottom = isNearBottom();
  autoScrollEnabled.value = nearBottom;
  if (nearBottom) {
    showJumpToLatest.value = false;
    unreadCount.value = 0;
    if (!isForceFollowActive()) {
      enableForceFollow(1200);
    }
  } else {
    forceFollowUntil.value = 0;
  }
}

async function followOrNotifyNewMessage(addUnread = false) {
  if (autoScrollEnabled.value || isForceFollowActive()) {
    await nextTick();
    scrollMessagesToBottom(false);
    return;
  }
  if (addUnread) {
    unreadCount.value += 1;
  }
  showJumpToLatest.value = true;
}

function jumpToLatest() {
  enableForceFollow(5000);
  scrollMessagesToBottom(true);
  unreadCount.value = 0;
}

function flushStreamUpdate(
  assistantIndex: number,
  content: string,
  createdTime: string | undefined,
  modelName: string | undefined
) {
  if (assistantIndex < 0 || assistantIndex >= messages.value.length) return;
  messages.value[assistantIndex] = {
    ...messages.value[assistantIndex],
    content: content || t('chat.state.thinking'),
    pending: true,
    created_time: createdTime || new Date().toISOString(),
    model_name: modelName
  };
}

async function loadConfig() {
  try {
    chatConfig.value = await getChatConfig();
  } catch {
    chatConfig.value = null;
  }
}

let loadHistoryImpl: (sessionId: string, page?: number | 'last') => Promise<void> = async () => {};

async function selectSession(sessionId: string, reloadHistory = true) {
  abortActiveChat();
  currentSessionId.value = sessionId;
  currentSessionTitle.value = findSessionTitle(sessionId);
  resetConversation();
  resetHistoryPage();
  historyError.value = '';
  if (reloadHistory) {
    await loadHistoryImpl(sessionId, 'last');
  }
}

const {
  sessions,
  sessionLoading,
  sessionError,
  sessionPagination,
  sessionTotalCount,
  loadSessions,
  changeSessionPage,
  findSessionTitle,
  ensureSessionVisible,
  applySessionTitle,
  requestSessionTitle
} = useChatSessions({
  defaultSessionTitle: () => t('chat.sessions.defaultTitle'),
  loadSessionsFailedMessage: () => t('chat.message.loadSessionsFailed'),
  currentSessionId,
  currentSessionTitle,
  selectSession,
  resetConversation,
  onSilentLoadError: (message) => setNotice('warning', message)
});

const {
  historyLoading,
  historyError,
  historyPagination,
  loadHistory,
  reloadCurrentHistory: reloadCurrentHistoryForSession,
  changeHistoryPage: changeHistoryPageForSession,
  refreshHistoryPagination: refreshHistoryPaginationForSession,
  resetHistoryPage
} = useChatHistory<DisplayMessage>({
  messages,
  loadHistoryFailedMessage: () => t('chat.message.loadHistoryFailed'),
  normalizeMessages,
  resolveSessionTitle: (sessionId) => findSessionTitle(sessionId),
  updateSessionTitle: (title) => {
    currentSessionTitle.value = title;
  },
  onLoaded: async () => {
    restorePendingAction(messages.value);
    await nextTick();
    scrollMessagesToBottom(true);
  },
  onEmptyHistory: () => {
    restorePendingAction([]);
  }
});

loadHistoryImpl = loadHistory;

function reloadCurrentHistory() {
  void reloadCurrentHistoryForSession(currentSessionId.value);
}

function refreshHistoryPagination() {
  return refreshHistoryPaginationForSession(currentSessionId.value);
}

function changeHistoryPage(page: number) {
  void changeHistoryPageForSession(currentSessionId.value, page);
}

const messageCountLabel = computed(() =>
  t('chat.messageCount', { count: historyPagination.value.total || messages.value.length })
);

const chatToolbarHintText = computed(() => chatBanner.value?.message?.trim() ?? '');
const showChatToolbarHint = computed(() => Boolean(chatToolbarHintText.value));

async function handleNewSession() {
  try {
    const result = await createChatSession();
    const sessionId = result.session_id || result.session?.session_id || '';
    currentSessionId.value = sessionId;
    currentSessionTitle.value = result.session?.title || '';
    resetConversation();
    suggestedQuestions.value = [];
    ensureSessionVisible(sessionId, currentSessionTitle.value);
    void loadSessions(false, 1, true);
    setNotice('success', t('chat.message.newSessionReady'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.createSessionFailed')));
  }
}

const renamingSessionId = ref('');
const renameDraft = ref('');

function startRename(session: ChatSessionRecord) {
  renamingSessionId.value = session.session_id;
  renameDraft.value = displaySessionTitle(session.title);
}

function cancelRename() {
  renamingSessionId.value = '';
  renameDraft.value = '';
}

async function submitRename(sessionId: string) {
  const title = renameDraft.value.trim();
  if (!title) {
    setNotice('warning', t('chat.message.renameSessionEmpty'));
    return;
  }
  try {
    sessionLoading.value = true;
    await updateChatSession(sessionId, { title });
    applySessionTitle(sessionId, title, 'manual');
    cancelRename();
    setNotice('success', t('chat.message.renameSessionSuccess'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.renameSessionFailed')));
  } finally {
    sessionLoading.value = false;
  }
}

async function handleDeleteSession(sessionId: string) {
  if (!sessionId || sessionLoading.value) return;
  const target = sessions.value.find((item) => item.session_id === sessionId);
  pendingDeleteSessionId.value = sessionId;
  pendingDeleteSessionTitle.value = displaySessionTitle(target?.title);
  deleteConfirmVisible.value = true;
}

function cancelDeleteSession() {
  pendingDeleteSessionId.value = '';
  pendingDeleteSessionTitle.value = '';
}

async function confirmDeleteSession() {
  const sessionId = pendingDeleteSessionId.value;
  if (!sessionId || sessionLoading.value) {
    cancelDeleteSession();
    return;
  }
  try {
    sessionLoading.value = true;
    await deleteChatSession(sessionId);
    const isCurrent = currentSessionId.value === sessionId;
    if (isCurrent) {
      currentSessionId.value = '';
      currentSessionTitle.value = '';
      resetConversation();
    }

    await loadSessions(true, sessionPagination.value.page);

    if (isCurrent && sessions.value.length > 0) {
      await selectSession(sessions.value[0].session_id, true);
    }
    setNotice('success', t('chat.message.deleteSessionSuccess'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.deleteSessionFailed')));
  } finally {
    cancelDeleteSession();
    sessionLoading.value = false;
  }
}

async function refreshCurrentSession() {
  if (!currentSessionId.value) {
    await loadSessions();
    return;
  }
  await Promise.all([loadSessions(false, sessionPagination.value.page), loadHistory(currentSessionId.value, historyPagination.value.page)]);
}

function createPlaceholderAssistant() {
  const key = `assistant-${Date.now()}-${messageCounter.value += 1}`;
  pendingAssistantKey.value = key;
  messages.value.push({
    key,
    role: 'assistant',
    content: t('chat.state.thinking'),
    pending: true
  });
}

function updateAssistantMessage(
  assistantIndex: number,
  content: string,
  options?: { createdTime?: string; modelName?: string; pending?: boolean; role?: DisplayMessage['role'] }
) {
  if (assistantIndex < 0 || assistantIndex >= messages.value.length) return;
  const role = options?.role || messages.value[assistantIndex].role;
  messages.value[assistantIndex] = {
    ...messages.value[assistantIndex],
    role,
    content: normalizeDisplayContent(content || t('chat.state.emptyMessage'), role),
    pending: options?.pending ?? false,
    created_time: options?.createdTime || new Date().toISOString(),
    model_name: options?.modelName
  };
}

const handleSend = createChatSendHandler({
  t,
  draftMessage,
  messages,
  currentSessionId,
  currentSessionTitle,
  chatConfig,
  pendingAssistantKey,
  suggestedQuestions,
  streamEnabled,
  smartReplyEnabled,
  messageCounter,
  autoScrollEnabled,
  sendLoading,
  abortActiveChat,
  beginAbortableRequest,
  isAbortError,
  resetPendingAction,
  clearChatBanner,
  ensureSessionVisible,
  createPlaceholderAssistant,
  enableForceFollow,
  scrollMessagesToBottom,
  flushStreamUpdate,
  updateAssistantMessage,
  followOrNotifyNewMessage,
  resetHistoryPage,
  refreshHistoryPagination,
  loadSessions,
  requestSessionTitle,
  setNotice
});

async function handleSuggestionClick(suggestion: string, event?: MouseEvent) {
  const text = String(suggestion || '').trim();
  if (!text || sendLoading.value) return;
  void trackQuickReplyFeedback({
    suggestion_text: text,
    was_clicked: true,
    session_id: currentSessionId.value || undefined
  }).catch(() => undefined);

  if (event?.shiftKey && looksLikeGenerateCasesSuggestion(text)) {
    await router.push({
      path: '/cases/generate',
      query: { prefill: text }
    });
    setNotice('info', t('chat.experimentalTools.openStandaloneHint'));
    return;
  }

  draftMessage.value = text;
  await handleSend({ source: 'quick_reply' });
}

async function handleExport() {
  if (!currentSessionId.value) return;
  try {
    exportLoading.value = true;
    const result = await exportChatHistory(currentSessionId.value, 'json');
    triggerBlobDownload(result.blob, result.filename || 'chat_history.json', 'chat_history.json');
    setNotice('success', t('chat.message.exportSuccess'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.exportFailed')));
  } finally {
    exportLoading.value = false;
  }
}

async function handleInsertTemplate() {
  if (sendLoading.value) return;
  try {
    if (!templatePreviewContent.value.trim()) {
      await loadTemplatePreview(selectedTemplateType.value);
    }
    const content = String(templatePreviewContent.value || '').trim();
    if (!content) {
      setNotice('warning', t('chat.message.templateEmpty'));
      return;
    }
    draftMessage.value = draftMessage.value.trim()
      ? `${draftMessage.value.trim()}\n\n${content}`
      : content;
    setNotice('success', t('chat.message.templateInserted'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.templateLoadFailed')));
  }
}

async function loadTemplatePreview(templateType: string) {
  templatePreviewLoading.value = true;
  try {
    const result = await getChatTemplate(templateType, String(locale.value || 'zh-CN'));
    templatePreviewContent.value = String(result.template?.content || '').trim();
  } catch {
    templatePreviewContent.value = '';
  } finally {
    templatePreviewLoading.value = false;
  }
}

async function handleTemplateTypeChange() {
  await loadTemplatePreview(selectedTemplateType.value);
}

async function handleClearCurrentSession() {
  if (!canClearConversation.value || sendLoading.value) return;
  clearConfirmVisible.value = true;
}

async function confirmClearCurrentSession() {
  clearConfirmVisible.value = false;
  if (!messages.value.length) {
    // Nothing persisted yet; clear local composer/suggestions directly.
    draftMessage.value = '';
    suggestedQuestions.value = [];
    setNotice('success', t('chat.message.clearSessionSuccess'));
    return;
  }

  if (!currentSessionId.value) {
    // Local-only draft conversation: clear directly without server round-trip.
    resetConversation();
    historyPagination.value = {
      page: 1,
      per_page: historyPagination.value.per_page,
      total: 0,
      pages: 0,
      has_prev: false,
      has_next: false
    };
    suggestedQuestions.value = [];
    setNotice('success', t('chat.message.clearSessionSuccess'));
    return;
  }

  try {
    await clearChatHistory(currentSessionId.value);
    resetConversation();
    historyPagination.value = {
      page: 1,
      per_page: historyPagination.value.per_page,
      total: 0,
      pages: 0,
      has_prev: false,
      has_next: false
    };
    suggestedQuestions.value = [];
    void loadSessions(false, sessionPagination.value.page || 1, true);
    setNotice('success', t('chat.message.clearSessionSuccess'));
  } catch (error) {
    setNotice('danger', getUserFacingErrorMessage(error, t('chat.message.clearSessionFailed')));
  }
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadSessions(false)]);
  await loadTemplatePreview(selectedTemplateType.value);
  // Enter-chat creates a local draft conversation only.
  // Persisted session is created when first message is sent.
  currentSessionId.value = '';
  currentSessionTitle.value = '';
  resetConversation();
});

watch(
  () => locale.value,
  async () => {
    await loadTemplatePreview(selectedTemplateType.value);
  }
);

watch(
  () => [suggestedQuestions.value.length, smartReplyEnabled.value] as const,
  ([count, enabled]) => {
    if (enabled && count > 0) void refreshQuickReplyStats();
  }
);

onBeforeUnmount(() => {
  abortActiveChat();
});
</script>
