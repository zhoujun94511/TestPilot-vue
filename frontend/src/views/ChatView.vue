<template>
  <section class="tp-container-fluid tp-py-3 tp-page tp-page-shell tp-chat-page">
    <ActionBar :title="t('chat.page.title')" :subtitle="t('chat.page.subtitle')">
      <template #actions>
        <TpButton variant="ghost" :disabled="sessionLoading || sendLoading" @click="handleNewSession">
          {{ t('chat.actions.newSession') }}
        </TpButton>
        <TpButton variant="secondary" :loading="sessionLoading" :disabled="sessionLoading || !currentSessionId" @click="refreshCurrentSession">
          {{ t('chat.actions.refresh') }}
        </TpButton>
        <TpButton variant="success" :loading="exportLoading" :disabled="exportLoading || !currentSessionId" @click="handleExport">
          {{ exportLoading ? t('chat.actions.exporting') : t('chat.actions.export') }}
        </TpButton>
        <TpButton variant="danger" :disabled="sendLoading || !canClearConversation" @click="handleClearCurrentSession">
          {{ t('chat.actions.clearSession') }}
        </TpButton>
      </template>
    </ActionBar>

    <div v-if="notice" class="tp-risk-block tp-mb-3" :class="noticeClass">
      <div class="tp-flex tp-align-start tp-justify-between tp-gap-3">
        <div class="tp-flex-grow-1">{{ notice }}</div>
        <TpButton variant="ghost" size="sm" :aria-label="t('common.actions.close')" @click="notice = ''">
          {{ t('common.actions.close') }}
        </TpButton>
      </div>
    </div>

    <div class="tp-row tp-g-3 tp-align-stretch">
      <aside class="tp-col-12 tp-col-xl-3">
        <TpCard>
          <template #header>
            <div>
              <div class="tp-section-title">{{ t('chat.sessions.title') }}</div>
              <div class="tp-section-subtitle">{{ t('chat.sessions.count', { count: sessionTotalCount }) }}</div>
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
          />
          <div v-else class="tp-grid tp-gap-2">
            <div
              v-for="session in sessions"
              :key="session.session_id"
              class="tp-nav-item tp-chat-session"
              :class="{ 'tp-chat-session--active': session.session_id === currentSessionId }"
              @click="selectSession(session.session_id)"
            >
              <div class="tp-chat-session__main">
                <input
                  v-if="renamingSessionId === session.session_id"
                  v-model="renameDraft"
                  class="tp-input"
                  :disabled="sessionLoading || sendLoading"
                  @click.stop
                  @keydown.enter.stop.prevent="submitRename(session.session_id)"
                  @keydown.esc.stop.prevent="cancelRename"
                />
                <div v-else class="tp-data-title text-truncate">{{ session.title || t('chat.sessions.untitled') }}</div>
                <div class="tp-small text-truncate" style="color: var(--tp-color-text-500)">{{ sessionPreview(session) }}</div>
              </div>
              <div class="tp-chat-session__actions">
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
                  class="tp-chat-session__delete"
                  :disabled="sessionLoading || sendLoading"
                  @click.stop="handleDeleteSession(session.session_id)"
                >
                  {{ t('chat.actions.deleteSession') }}
                </TpButton>
              </div>
            </div>
            <TpPager
              class="tp-pt-1"
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

      <section class="tp-col-12 tp-col-xl-9">
        <TpCard class="tp-flex tp-flex-column tp-h-100 tp-chat-main-card">
          <template #header>
            <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-start tp-gap-2">
              <div>
                <div class="tp-section-title">{{ currentSessionTitle }}</div>
                <div class="tp-section-subtitle">
                  <span v-if="currentSessionId">{{ t('chat.sessions.currentId') }}</span>
                  <span v-else>{{ t('chat.sessions.noSessionSelected') }}</span>
                </div>
              </div>
              <TpTag variant="neutral">
                <span v-if="historyLoading">{{ t('chat.state.loadingHistory') }}</span>
                <span v-else>{{ messageCountLabel }}</span>
              </TpTag>
            </div>
          </template>

          <div ref="messagePanelRef" class="tp-flex-grow-1 chat-message-panel tp-mb-3" @scroll="handleMessagePanelScroll">
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
              <div class="tp-chat-empty-state tp-mt-3">
                <p class="tp-mb-0">{{ t('chat.state.welcomeLead') }}</p>
                <p class="tp-mb-0 tp-mt-1">{{ t('chat.state.welcomePrompt') }}</p>
                <ul class="tp-mb-0 tp-mt-1 tp-chat-empty-list">
                  <li v-for="(question, index) in emptyStarterQuestions" :key="`empty-starter-${index}`">
                    <button
                      type="button"
                      class="tp-chat-empty-question"
                      :disabled="sendLoading"
                      @click="draftMessage = question"
                    >
                      {{ question }}
                    </button>
                  </li>
                </ul>
              </div>
            </BaseState>
            <div v-else class="chat-message-list">
              <div
                v-for="message in messages"
                :key="message.key"
                class="tp-flex"
                :class="message.role === 'user' ? 'tp-justify-end' : 'tp-justify-start'"
              >
                <div v-if="message.role === 'user'" class="chat-user-card">
                  <div class="tp-small" style="color: var(--tp-color-text-500)">
                    {{ resolveRoleLabel(message.role) }}
                    <span v-if="message.created_time">- {{ formatDateTime(message.created_time) }}</span>
                  </div>
                  <ChatMessageContent class="tp-mt-2" :content="message.content || t('chat.state.emptyMessage')" :role="message.role" />
                </div>

                <div v-else-if="message.role === 'system'" class="chat-assistant-card chat-assistant-card--system">
                  <div class="tp-small chat-meta">
                    {{ resolveRoleLabel(message.role) }}
                    <span v-if="message.created_time">- {{ formatDateTime(message.created_time) }}</span>
                  </div>
                  <ChatMessageContent class="tp-mt-2" :content="message.content || t('chat.state.emptyMessage')" :role="message.role" />
                </div>

                <div v-else class="chat-assistant-card">
                  <div class="tp-small chat-meta">
                    {{ resolveRoleLabel(message.role) }}
                    <span class="ms-1">{{ localizeModelStatus(message.model_name || sessionModelLabel) }}</span>
                    <span v-if="message.created_time">- {{ formatDateTime(message.created_time) }}</span>
                  </div>
                  <ChatMessageContent class="tp-mt-2" :content="message.content || t('chat.state.emptyMessage')" :role="message.role" />
                </div>
              </div>
            </div>
            <TpPager
              v-if="!historyLoading && !historyError"
              class="tp-mt-3"
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
            <div v-if="suggestedQuestions.length" class="chat-suggestions tp-mt-3">
              <div class="tp-small chat-meta tp-mb-2 tp-flex tp-justify-between tp-align-center tp-gap-2">
                <span>{{ t('chat.quickReply.title') }}</span>
              </div>
              <div class="tp-flex tp-flex-wrap tp-gap-2">
                <TpButton
                  v-for="(suggestion, index) in suggestedQuestions"
                  :key="`suggestion-${index}-${suggestion}`"
                  variant="secondary"
                  size="sm"
                  :disabled="sendLoading"
                  @click="handleSuggestionClick(suggestion)"
                >
                  {{ suggestion }}
                </TpButton>
              </div>
            </div>
            <TpButton
              v-if="showJumpToLatest"
              class="chat-jump-latest"
              variant="secondary"
              size="sm"
              @click="jumpToLatest"
            >
              {{ t('chat.actions.jumpToLatest', { count: unreadCount }) }}
            </TpButton>
          </div>

          <form class="chat-composer" @submit.prevent="handleSend">
            <label class="tp-form-label">{{ t('chat.composer.label') }}</label>
            <div v-if="templatePanelEnabled" class="tp-chat-template-panel tp-mb-2">
              <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-center tp-gap-2">
                <div class="tp-small chat-meta">{{ t('chat.template.selectLabel') }}</div>
                <div class="tp-flex tp-align-center tp-gap-2">
                  <select
                    v-model="selectedTemplateType"
                    class="tp-select tp-chat-template-select"
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
              <div class="tp-chat-template-preview tp-mt-2">
                <div v-if="templatePreviewLoading" class="tp-small chat-meta">{{ t('chat.template.loading') }}</div>
                <div v-else-if="templatePreviewContent" class="tp-small">{{ templatePreviewContent }}</div>
                <div v-else class="tp-small chat-meta">{{ t('chat.template.empty') }}</div>
              </div>
            </div>
            <textarea
              v-model.trim="draftMessage"
              class="tp-textarea"
              rows="4"
              :placeholder="t('chat.composer.placeholder')"
              :disabled="sendLoading"
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>

            <div v-if="pendingActionExecutionId" class="tp-chat-action-panel tp-mt-2">
              <div class="tp-small chat-meta tp-mb-1">{{ t('chat.action.pendingTitle') }}</div>
              <div v-if="showHighRiskHint" class="tp-chat-action-risk-hint tp-small tp-mb-2">
                {{ t('chat.action.highRiskHint') }}
              </div>
              <div class="tp-small tp-mb-1">
                {{ t('chat.action.executionId') }}: <code>{{ pendingActionExecutionId }}</code>
              </div>
              <div v-if="pendingActionPlan" class="tp-small tp-mb-2">
                <div class="chat-meta tp-mb-1">{{ t('chat.action.plan') }}</div>
                <div class="tp-chat-action-grid">
                  <span class="chat-meta">{{ t('chat.action.intent') }}</span>
                  <span>{{ pendingActionSummary.intent }}</span>
                  <span class="chat-meta">{{ t('chat.action.tool') }}</span>
                  <span>{{ pendingActionSummary.toolName }}</span>
                  <span class="chat-meta">{{ t('chat.action.risk') }}</span>
                  <span><TpTag :variant="pendingActionRiskVariant">{{ pendingActionSummary.riskLevel }}</TpTag></span>
                </div>
                <div v-if="pendingActionArgsEntries.length" class="tp-mt-2">
                  <div class="chat-meta tp-mb-1">{{ t('chat.action.args') }}</div>
                  <div class="tp-chat-action-grid">
                    <template v-for="item in pendingActionArgsEntries" :key="item.key">
                      <span class="chat-meta">{{ item.key }}</span>
                      <span>{{ item.value }}</span>
                    </template>
                  </div>
                </div>
              </div>
              <div v-if="pendingActionPreview" class="tp-small tp-mb-1">
                <div class="chat-meta tp-mb-1">{{ t('chat.action.preview') }}</div>
                <div v-if="pendingDeleteCasePreview" class="tp-chat-action-delete-preview tp-mb-2">
                  <div class="tp-chat-action-delete-preview__title">{{ t('chat.action.deletePreviewTitle') }}</div>
                  <div class="tp-small tp-mt-1">
                    <strong>ID:</strong> {{ pendingDeleteCasePreview.caseId }}
                  </div>
                  <div class="tp-small tp-mt-1">
                    <strong>{{ t('chat.action.field.title') }}:</strong> {{ pendingDeleteCasePreview.title }}
                  </div>
                  <div class="tp-small tp-mt-1">
                    <strong>{{ t('chat.action.field.status') }}:</strong> {{ pendingDeleteCasePreview.status }}
                  </div>
                </div>
                <div v-if="pendingActionPreviewSummary.length" class="tp-chat-action-grid tp-mb-2">
                  <template v-for="item in pendingActionPreviewSummary" :key="item.key">
                    <span class="chat-meta">{{ item.key }}</span>
                    <span>{{ item.value }}</span>
                  </template>
                </div>
                <pre class="tp-chat-action-preview">{{ formatJsonPreview(pendingActionPreview) }}</pre>
              </div>
              <div v-if="requireDeleteKeywordConfirm" class="tp-mt-2">
                <label class="tp-small chat-meta tp-mb-1 tp-d-block" for="deleteActionConfirmInput">
                  {{ t('chat.action.deleteConfirmLabel') }}
                </label>
                <input
                  id="deleteActionConfirmInput"
                  v-model.trim="deleteActionConfirmText"
                  type="text"
                  class="tp-input"
                  :placeholder="t('chat.action.deleteConfirmPlaceholder')"
                  :disabled="sendLoading"
                />
                <div class="tp-small tp-mt-1" :class="deleteConfirmSatisfied ? 'tp-text-success' : 'chat-meta'">
                  {{ deleteConfirmSatisfied ? t('chat.action.deleteConfirmReady') : t('chat.action.deleteConfirmPending') }}
                </div>
              </div>
            </div>

            <div class="tp-flex tp-flex-wrap tp-justify-between tp-align-center tp-gap-2 tp-mt-3 tp-chat-composer-footer">
              <div class="tp-chat-toggle-group">
                <label
                  class="tp-chat-switch"
                  :class="{ 'tp-chat-switch--on': streamEnabled }"
                  for="chatStreamEnabled"
                >
                  <input
                    id="chatStreamEnabled"
                    v-model="streamEnabled"
                    class="tp-chat-switch__input"
                    type="checkbox"
                    @change="persistChatBooleanSetting('streamEnabled', streamEnabled)"
                  />
                  <span class="tp-chat-switch__track" aria-hidden="true">
                    <span class="tp-chat-switch__thumb"></span>
                  </span>
                  <span class="tp-chat-switch__state" :class="{ 'tp-chat-switch__state--on': streamEnabled }">
                    {{ switchStateLabel(streamEnabled) }}
                  </span>
                  <span class="tp-chat-switch__text">{{ t('chat.composer.streamToggle') }}</span>
                </label>
                <label
                  class="tp-chat-switch"
                  :class="{ 'tp-chat-switch--on': smartReplyEnabled }"
                  for="chatSmartReplyEnabled"
                >
                  <input
                    id="chatSmartReplyEnabled"
                    v-model="smartReplyEnabled"
                    class="tp-chat-switch__input"
                    type="checkbox"
                    @change="persistChatBooleanSetting('smartReplyEnabled', smartReplyEnabled)"
                  />
                  <span class="tp-chat-switch__track" aria-hidden="true">
                    <span class="tp-chat-switch__thumb"></span>
                  </span>
                  <span class="tp-chat-switch__state" :class="{ 'tp-chat-switch__state--on': smartReplyEnabled }">
                    {{ switchStateLabel(smartReplyEnabled) }}
                  </span>
                  <span class="tp-chat-switch__text">{{ t('chat.composer.smartReplyToggle') }}</span>
                </label>
                <label
                  class="tp-chat-switch"
                  :class="{ 'tp-chat-switch--on': templatePanelEnabled }"
                  for="chatTemplatePanelEnabled"
                >
                  <input
                    id="chatTemplatePanelEnabled"
                    v-model="templatePanelEnabled"
                    class="tp-chat-switch__input"
                    type="checkbox"
                    @change="persistChatBooleanSetting('templatePanelEnabled', templatePanelEnabled)"
                  />
                  <span class="tp-chat-switch__track" aria-hidden="true">
                    <span class="tp-chat-switch__thumb"></span>
                  </span>
                  <span class="tp-chat-switch__state" :class="{ 'tp-chat-switch__state--on': templatePanelEnabled }">
                    {{ switchStateLabel(templatePanelEnabled) }}
                  </span>
                  <span class="tp-chat-switch__text">{{ t('chat.composer.templateToggle') }}</span>
                </label>
                <label
                  class="tp-chat-switch"
                  :class="{ 'tp-chat-switch--on': experimentalActionsEnabled, 'tp-chat-switch--disabled': sendLoading }"
                  for="chatExperimentalActionsEnabled"
                >
                  <input
                    id="chatExperimentalActionsEnabled"
                    v-model="experimentalActionsEnabled"
                    class="tp-chat-switch__input"
                    type="checkbox"
                    :disabled="sendLoading"
                    @change="handleExperimentalActionsToggle"
                  />
                  <span class="tp-chat-switch__track" aria-hidden="true">
                    <span class="tp-chat-switch__thumb"></span>
                  </span>
                  <span class="tp-chat-switch__state" :class="{ 'tp-chat-switch__state--on': experimentalActionsEnabled }">
                    {{ switchStateLabel(experimentalActionsEnabled) }}
                  </span>
                  <span class="tp-chat-switch__text">{{ t('chat.composer.experimentalActionsToggle') }}</span>
                </label>
              </div>
              <div class="tp-flex tp-gap-2 tp-chat-composer-actions">
                <TpButton
                  v-if="pendingActionExecutionId"
                  variant="secondary"
                  :disabled="sendLoading || !canConfirmPendingAction"
                  @click="handleConfirmPendingAction"
                >
                  {{ t('chat.actions.confirmAction') }}
                </TpButton>
                <TpButton
                  v-if="pendingActionExecutionId"
                  variant="ghost"
                  :disabled="sendLoading"
                  @click="handleCancelPendingAction"
                >
                  {{ t('chat.actions.cancelAction') }}
                </TpButton>
                <TpButton
                  variant="danger"
                  :disabled="sendLoading || !canClearConversation"
                  @click="handleClearCurrentSession"
                >
                  {{ t('chat.actions.clearSession') }}
                </TpButton>
                <TpButton variant="secondary" :disabled="sendLoading || !draftMessage.trim()" @click="draftMessage = ''">
                  {{ t('common.actions.cancel') }}
                </TpButton>
                <TpButton type="submit" :loading="sendLoading" :disabled="sendLoading || !draftMessage.trim()">
                  {{ sendLoading ? t('chat.actions.sending') : t('chat.actions.send') }}
                </TpButton>
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
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import BaseState from '@/components/common/BaseState.vue';
import ChatMessageContentSkeleton from '@/components/chat/ChatMessageContentSkeleton.vue';
import TpButton from '@/components/ui/base/TpButton.vue';
import TpCard from '@/components/ui/base/TpCard.vue';
import TpPager from '@/components/ui/base/TpPager.vue';
import TpTag from '@/components/ui/base/TpTag.vue';
import {
  cancelExperimentalAction,
  clearChatHistory,
  confirmExperimentalAction,
  createChatSession,
  deleteChatSession,
  exportChatHistory,
  trackQuickReplyFeedback,
  updateChatSession,
  getChatConfig,
  getChatTemplate,
  getChatHistory,
  listChatSessions,
  sendChatMessage,
  streamChatMessage,
  type ChatMessageRecord,
  type ChatSessionRecord
} from '@/api/chat';
import { updateConfigItem } from '@/api/config';
import { ApiError } from '@/api/http';
import { ErrorCodes } from '@/constants/errorCodes';

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

const sessions = ref<ChatSessionRecord[]>([]);
const messages = ref<DisplayMessage[]>([]);
const currentSessionId = ref('');
const currentSessionTitle = ref(t('chat.sessions.defaultTitle'));
const draftMessage = ref('');
const sessionLoading = ref(false);
const historyLoading = ref(false);
const sendLoading = ref(false);
const exportLoading = ref(false);
const sessionError = ref('');
const historyError = ref('');
const notice = ref('');
const noticeType = ref<NoticeState['type']>('info');
const chatConfig = ref<Awaited<ReturnType<typeof getChatConfig>> | null>(null);
const pendingAssistantKey = ref('');
const suggestedQuestions = ref<string[]>([]);
const streamEnabled = ref(readChatBooleanSetting('streamEnabled', true));
const smartReplyEnabled = ref(readChatBooleanSetting('smartReplyEnabled', true));
const templatePanelEnabled = ref(readChatBooleanSetting('templatePanelEnabled', true));
const experimentalActionsEnabled = ref(false);
const pendingActionExecutionId = ref('');
const pendingActionPlan = ref<Record<string, unknown> | null>(null);
const pendingActionPreview = ref<Record<string, unknown> | null>(null);
const deleteActionConfirmText = ref('');
const selectedTemplateType = ref('test_strategy');
const templatePreviewLoading = ref(false);
const templatePreviewContent = ref('');
const messageCounter = ref(0);
const messagePanelRef = ref<HTMLElement | null>(null);
let streamFlushTimer: number | null = null;
const autoScrollEnabled = ref(true);
const forceFollowUntil = ref(0);
const showJumpToLatest = ref(false);
const unreadCount = ref(0);
const deleteConfirmVisible = ref(false);
const pendingDeleteSessionId = ref('');
const pendingDeleteSessionTitle = ref('');
const clearConfirmVisible = ref(false);
let loadSessionsRequestSeq = 0;
let loadHistoryRequestSeq = 0;
const sessionPagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});
const historyPagination = ref({
  page: 1,
  per_page: 50,
  total: 0,
  pages: 0,
  has_prev: false,
  has_next: false
});

const noticeClass = computed(() => ({
  'tp-risk-block--info': noticeType.value === 'info',
  'tp-risk-block--danger': noticeType.value === 'danger',
  'tp-risk-block--warning': noticeType.value === 'warning',
  'tp-risk-block--success': noticeType.value === 'success'
}));

const sessionTotalCount = computed(() => sessionPagination.value.total || sessions.value.length);
const messageCountLabel = computed(() => t('chat.messageCount', { count: historyPagination.value.total || messages.value.length }));
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
function readChatBooleanSetting(key: string, fallback: boolean) {
  try {
    const raw = localStorage.getItem(`chat.${key}`);
    if (raw === '1') return true;
    if (raw === '0') return false;
    return fallback;
  } catch {
    return fallback;
  }
}

function persistChatBooleanSetting(key: string, value: boolean) {
  try {
    localStorage.setItem(`chat.${key}`, value ? '1' : '0');
  } catch {
    // Ignore storage failures (private mode etc.)
  }
}

function switchStateLabel(enabled: boolean) {
  const isZh = String(locale.value || '').toLowerCase().startsWith('zh');
  if (isZh) return enabled ? '开' : '关';
  return enabled ? 'ON' : 'OFF';
}

function setNotice(type: NoticeState['type'], message: string) {
  noticeType.value = type;
  notice.value = message;
}

function clearNotice() {
  notice.value = '';
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function sessionPreview(session: ChatSessionRecord) {
  const preview = session.last_activity ? formatDateTime(session.last_activity) : '';
  return preview || t('chat.sessions.emptyPreview');
}

function resolveRoleLabel(role: string) {
  if (role === 'user') return t('chat.roles.user');
  if (role === 'assistant') return t('chat.roles.assistant');
  return t('chat.roles.system');
}

function localizeModelStatus(value: string | null | undefined) {
  const raw = String(value || '').trim();
  if (!raw) return t('chat.sessions.defaultTitle');
  const normalized = raw.toLowerCase();
  const modelStatusMap: Record<string, string> = {
    '配置错误': t('chat.modelStatus.configError'),
    '服务不可用': t('chat.modelStatus.serviceUnavailable'),
    '连接失败': t('chat.modelStatus.connectionFailed'),
    '未知模型': t('chat.modelStatus.unknownModel'),
    'config error': t('chat.modelStatus.configError'),
    'configuration error': t('chat.modelStatus.configError'),
    'service unavailable': t('chat.modelStatus.serviceUnavailable'),
    'connection failed': t('chat.modelStatus.connectionFailed'),
    'unknown model': t('chat.modelStatus.unknownModel')
  };
  return modelStatusMap[raw] || modelStatusMap[normalized] || raw;
}

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
  const lines = raw.split('\n');
  const filtered = lines.filter((line, index) => {
    if (index > 8) return true;
    const text = line.trim();
    if (!text) return true;
    return !(
      /^\*\*(状态|工具|总数|命中数|检索状态|生成数量|RAG)\*\*[:：]/.test(text)
      || /^\*\*(Status|Tool|Total|Hits|Search status|Generated|RAG)\*\*[:：]/i.test(text)
    );
  });
  return filtered.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

function isGenericSuccessMessage(text: string): boolean {
  const normalized = String(text || '').trim().toLowerCase();
  return normalized === 'message sent successfully'
    || normalized === '动作执行成功'
    || normalized === '操作成功'
    || normalized === 'success'
    || normalized === 'ok';
}

function findSessionTitle(sessionId: string) {
  return sessions.value.find((item) => item.session_id === sessionId)?.title || t('chat.sessions.defaultTitle');
}

function ensureSessionVisible(sessionId: string, title: string) {
  if (!sessionId) return;
  const index = sessions.value.findIndex((item) => item.session_id === sessionId);
  if (index >= 0) {
    const current = sessions.value[index];
    sessions.value[index] = {
      ...current,
      title: title || current.title || t('chat.sessions.defaultTitle'),
      last_activity: new Date().toISOString()
    };
  } else {
    sessions.value = [
      {
        session_id: sessionId,
        title: title || t('chat.sessions.defaultTitle'),
        last_activity: new Date().toISOString(),
        message_count: 0,
        total_tokens: 0
      },
      ...sessions.value
    ];
  }
  sessionPagination.value.total = Math.max(sessionPagination.value.total || 0, sessions.value.length);
}

function resetConversation() {
  messages.value = [];
  suggestedQuestions.value = [];
  historyError.value = '';
  draftMessage.value = '';
  pendingAssistantKey.value = '';
  messageCounter.value = 0;
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
    // User manually moved away from bottom, stop forced sticking.
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
    experimentalActionsEnabled.value = Boolean(chatConfig.value?.experimental_actions_enabled);
  } catch {
    chatConfig.value = null;
    experimentalActionsEnabled.value = false;
  }
}

async function handleExperimentalActionsToggle() {
  const nextValue = Boolean(experimentalActionsEnabled.value);
  try {
    await updateConfigItem('ENABLE_EXPERIMENTAL_ACTIONS', {
      value: nextValue,
      value_type: 'bool',
      category: 'general',
      description: 'Enable experimental action runtime',
      is_sensitive: false
    });
    await loadConfig();
    setNotice('success', t('chat.message.experimentalToggleSuccess'));
  } catch (error) {
    experimentalActionsEnabled.value = !nextValue;
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.experimentalToggleFailed'));
  }
}

function resetPendingAction() {
  pendingActionExecutionId.value = '';
  pendingActionPlan.value = null;
  pendingActionPreview.value = null;
  deleteActionConfirmText.value = '';
}

let activeChatAbort: AbortController | null = null;

function abortActiveChat() {
  activeChatAbort?.abort();
  activeChatAbort = null;
}

function isAbortError(error: unknown) {
  if (activeChatAbort?.signal.aborted) return true;
  return error instanceof DOMException && error.name === 'AbortError';
}

function restorePendingAction(items: Array<{ content?: string }>) {
  resetPendingAction();
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const content = String(items[index]?.content || '');
    const idMatch = content.match(/执行ID:\s*`([^`]+)`/);
    if (!idMatch) continue;
    const statusMatch = content.match(/"status"\s*:\s*"([^"]+)"/);
    if (statusMatch?.[1] === 'needs_confirmation') {
      pendingActionExecutionId.value = idMatch[1];
      const toolMatch = content.match(/"tool"\s*:\s*"([^"]+)"/);
      const toolName = toolMatch?.[1] || '';
      pendingActionPlan.value = {
        tool_name: toolName,
        risk_level: toolName === 'delete_case' ? 'high' : 'low',
        requires_confirmation: true
      };
    }
    return;
  }
}

function formatJsonPreview(value: unknown) {
  if (!value || typeof value !== 'object') return '';
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function toDisplayValue(value: unknown) {
  if (value == null) return '-';
  if (typeof value === 'string') return value || '-';
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => toDisplayValue(item)).join(', ') : '-';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function parseMaybeJsonArray(value: unknown): unknown[] | null {
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string') return null;
  const text = value.trim();
  if (!text.startsWith('[') || !text.endsWith(']')) return null;
  try {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function stripLeadingOrderMarker(text: string): string {
  return String(text || '')
    .replace(/^\s*(?:\d+[\.\)、)]|[（(]?\d+[）)]|[一二三四五六七八九十]+[、\.])\s*/, '')
    .trim();
}

function hasLeadingOrderMarker(text: string): boolean {
  const value = String(text || '');
  return /^\s*(?:\d+[\.\)、)]|[（(]?\d+[）)]|[一二三四五六七八九十]+[、\.])\s*/.test(value);
}

function formatTextList(value: unknown, maxItems = 4, enableOrderNormalize = false): string {
  if (typeof value === 'string' && !value.trim().startsWith('[')) {
    const text = String(value || '').trim();
    if (!text) return '-';
    if (!enableOrderNormalize) return text;
    return hasLeadingOrderMarker(text) ? text : stripLeadingOrderMarker(text);
  }
  const parsedList = parseMaybeJsonArray(value);
  const list = parsedList || (Array.isArray(value) ? value : []);
  if (!list.length) return '-';
  return list
    .slice(0, maxItems)
    .map((item, index) => {
      const text = String(toDisplayValue(item) || '').trim();
      if (!text) return `${index + 1}. -`;
      if (!enableOrderNormalize) return `${index + 1}. ${text}`;
      if (hasLeadingOrderMarker(text)) return text;
      return `${index + 1}. ${stripLeadingOrderMarker(text)}`;
    })
    .join('\n');
}

function formatCasesAsMarkdown(items: unknown[]): string {
  const lines: string[] = [];
  const maxCount = 10;
  for (const raw of items.slice(0, maxCount)) {
    const item = asRecord(raw);
    if (!item) continue;
    lines.push(`### ${toDisplayValue(item.title)}`);
    lines.push(`- ID: \`${toDisplayValue(item.case_id)}\``);
    lines.push(`- 优先级: ${toDisplayValue(item.priority)} | 状态: ${toDisplayValue(item.status)} | 分类: ${toDisplayValue(item.category)}`);
    lines.push(`- 模块: ${toDisplayValue(item.module)} | 方法: ${toDisplayValue(item.test_method)}`);
    lines.push(`- 前置条件:\n${formatTextList(item.precondition, 3, true)}`);
    lines.push(`- 执行步骤:\n${formatTextList(item.steps, 3, true)}`);
    lines.push(`- 预期结果:\n${formatTextList(item.expected_result, 3, true)}`);
    lines.push('');
  }
  if (items.length > maxCount) {
    lines.push(`> 仅展示前 ${maxCount} 条，共 ${items.length} 条`);
    lines.push('> 更多请前往「用例管理」页面查看。');
  }
  return lines.join('\n').trim();
}

function extractCaseIds(items: unknown[]): string[] {
  return items
    .map((raw) => asRecord(raw))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .map((item) => String(item.case_id || '').trim())
    .filter(Boolean);
}

function buildHighlightCasesLink(caseIds: string[]): string {
  const ids = caseIds.filter(Boolean).slice(0, 12);
  if (!ids.length) return '[用例管理](/cases/manage)';
  const hids = ids.join(',');
  return `[查看并高亮新用例](/cases/manage?from=generate&hids=${hids}&at=action_chat)`;
}

function extractRequirementIds(items: unknown[]): string[] {
  return items
    .map((raw) => asRecord(raw))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .map((item) => String(item.req_id || '').trim())
    .filter(Boolean);
}

function buildHighlightRequirementsLink(reqIds: string[]): string {
  const ids = reqIds.filter(Boolean).slice(0, 20);
  if (!ids.length) return '[文档管理](/documents/manage)';
  const rids = ids.join(',');
  return `[查看并高亮需求](/documents/manage?fromRequirements=1&rids=${rids}&at=action_chat)`;
}

function formatRequirementsAsMarkdown(items: unknown[]): string {
  const lines: string[] = [];
  const maxCount = 10;
  for (const raw of items.slice(0, maxCount)) {
    const item = asRecord(raw);
    if (!item) continue;
    lines.push(`### ${toDisplayValue(item.title)}`);
    lines.push(`- 需求ID: \`${toDisplayValue(item.req_id)}\``);
    lines.push(`- 类型: ${toDisplayValue(item.type)} | 优先级: ${toDisplayValue(item.priority)} | 状态: ${toDisplayValue(item.status)}`);
    lines.push(`- 来源文件: ${toDisplayValue(item.source_file)}`);
    lines.push(`- 内容摘要: ${toDisplayValue(item.content).slice(0, 220)}${String(toDisplayValue(item.content)).length > 220 ? '...' : ''}`);
    lines.push('');
  }
  if (items.length > maxCount) {
    lines.push(`> 仅展示前 ${maxCount} 条，共 ${items.length} 条`);
    lines.push('> 更多请前往「文档管理」页面查看。');
  }
  return lines.join('\n').trim();
}

function resolveDocText(doc: Record<string, unknown>): string {
  const candidates = [
    doc.content,
    doc.page_content,
    doc.text,
    doc.chunk_text,
    doc.snippet,
  ];
  for (const item of candidates) {
    const text = String(item ?? '').trim();
    if (text) return text;
  }
  return '';
}

function resolveDocSource(doc: Record<string, unknown>): string {
  const metadata = asRecord(doc.metadata);
  const candidates = [
    doc.source,
    doc.file_name,
    doc.filename,
    metadata?.source,
    metadata?.file_name,
  ];
  for (const item of candidates) {
    const text = String(item ?? '').trim();
    if (text) return text;
  }
  return '-';
}

function resolveDocScore(doc: Record<string, unknown>): string {
  const metadata = asRecord(doc.metadata);
  const candidates = [doc.score, doc.similarity, metadata?.score, metadata?.similarity];
  for (const item of candidates) {
    if (item == null) continue;
    const num = Number(item);
    if (Number.isFinite(num)) return num.toFixed(3);
  }
  return '-';
}

function formatKnowledgeDocsAsMarkdown(documents: unknown[]): string {
  const lines: string[] = [];
  const maxCount = 8;
  for (const raw of documents.slice(0, maxCount)) {
    const doc = asRecord(raw);
    if (!doc) continue;
    const content = resolveDocText(doc);
    lines.push(`### 文档片段`);
    lines.push(`- 来源: ${resolveDocSource(doc)}`);
    lines.push(`- 相关度: ${resolveDocScore(doc)}`);
    lines.push(`- 摘要: ${content ? `${content.slice(0, 260)}${content.length > 260 ? '...' : ''}` : '-'}`);
    lines.push('');
  }
  if (documents.length > maxCount) {
    lines.push(`> 仅展示前 ${maxCount} 条，共 ${documents.length} 条`);
  }
  return lines.join('\n').trim();
}

function formatAnalyzeResultAsMarkdown(result: Record<string, unknown>): string {
  const lines: string[] = [];
  lines.push(`**分析类型**: ${toDisplayValue(result.analysis_type)}`);
  lines.push(`**结果消息**: ${toDisplayValue(result.message)}`);
  const requirements = Array.isArray(result.requirements) ? result.requirements : [];
  const testPoints = Array.isArray(result.test_points) ? result.test_points : [];
  const businessRules = Array.isArray(result.business_rules) ? result.business_rules : [];
  if (requirements.length) {
    lines.push('');
    lines.push('### 识别的需求');
    lines.push(formatRequirementsAsMarkdown(requirements.slice(0, 6)));
  }
  if (testPoints.length) {
    lines.push('');
    lines.push('### 测试点');
    testPoints.slice(0, 10).forEach((item, index) => {
      lines.push(`${index + 1}. ${toDisplayValue(item)}`);
    });
  }
  if (businessRules.length) {
    lines.push('');
    lines.push('### 业务规则');
    businessRules.slice(0, 10).forEach((item, index) => {
      lines.push(`${index + 1}. ${toDisplayValue(item)}`);
    });
  }
  return lines.join('\n').trim();
}

function formatActionResultContent(
  messageText: string,
  status: string,
  toolName: string,
  toolResults: Record<string, unknown> | null
): string {
  void status;
  const cleanMessage = isGenericSuccessMessage(messageText) ? '' : String(messageText || '').trim();
  if (!toolResults) return cleanMessage || t('chat.state.emptyMessage');
  const parts: string[] = cleanMessage ? [cleanMessage] : [];
  if (toolName === 'list_cases') {
    const items = Array.isArray(toolResults.items) ? toolResults.items : [];
    if (items.length) {
      parts.push('');
      parts.push(formatCasesAsMarkdown(items));
      return parts.join('\n').trim() || t('chat.state.emptyMessage');
    }
  }
  if (toolName === 'generate_cases') {
    const items = Array.isArray(toolResults.items) ? toolResults.items : [];
    const cases = Array.isArray(toolResults.cases) ? toolResults.cases : [];
    const merged = items.length ? items : cases;
    const caseIds = extractCaseIds(merged);
    if (caseIds.length) {
      parts.push('');
      parts.push(`- 跳转: ${buildHighlightCasesLink(caseIds)}`);
    }
    if (merged.length) {
      parts.push('');
      parts.push(formatCasesAsMarkdown(merged));
      return parts.join('\n').trim() || t('chat.state.emptyMessage');
    }
  }
  if (toolName === 'list_requirements') {
    const items = Array.isArray(toolResults.items) ? toolResults.items : [];
    const reqIds = extractRequirementIds(items);
    if (reqIds.length) {
      parts.push('');
      parts.push(`- 跳转: ${buildHighlightRequirementsLink(reqIds)}`);
    }
    if (items.length) {
      parts.push('');
      parts.push(formatRequirementsAsMarkdown(items));
      return parts.join('\n').trim() || t('chat.state.emptyMessage');
    }
  }
  if (toolName === 'search_knowledge') {
    const docs = Array.isArray(toolResults.documents) ? toolResults.documents : [];
    if (toDisplayValue(toolResults.message) !== '-') {
      parts.push('');
      parts.push(`**提示**: ${toDisplayValue(toolResults.message)}`);
    }
    if (docs.length) {
      parts.push('');
      parts.push(formatKnowledgeDocsAsMarkdown(docs));
      return parts.join('\n').trim() || t('chat.state.emptyMessage');
    }
  }
  if (toolName === 'analyze_document_content') {
    parts.push('');
    parts.push(formatAnalyzeResultAsMarkdown(toolResults));
    return parts.join('\n').trim() || t('chat.state.emptyMessage');
  }
  if (toolName === 'delete_case') {
    parts.push(`**目标用例**: \`${toDisplayValue(toolResults.case_id)}\``);
    parts.push(`**标题**: ${toDisplayValue(toolResults.title)}`);
    parts.push(`**预演模式**: ${toDisplayValue(toolResults.dry_run)}`);
    parts.push(`**是否删除**: ${toDisplayValue(toolResults.deleted)}`);
    return parts.join('\n').trim() || t('chat.state.emptyMessage');
  }
  parts.push('');
  parts.push('```json');
  parts.push(formatJsonPreview(toolResults));
  parts.push('```');
  return parts.join('\n').trim() || t('chat.state.emptyMessage');
}

function localizeActionFieldKey(key: string) {
  const keyMap: Record<string, string> = {
    success: t('chat.action.field.success'),
    message: t('chat.action.field.message'),
    case_id: t('chat.action.field.caseId'),
    title: t('chat.action.field.title'),
    status: t('chat.action.field.status'),
    deleted: t('chat.action.field.deleted'),
    dry_run: t('chat.action.field.dryRun'),
    total: t('chat.action.field.total'),
    count: t('chat.action.field.count'),
    use_rag: t('chat.action.field.useRag')
  };
  return keyMap[key] || key;
}

const pendingActionSummary = computed(() => {
  const plan = pendingActionPlan.value || {};
  return {
    intent: toDisplayValue(plan.intent),
    toolName: toDisplayValue(plan.tool_name),
    riskLevel: toDisplayValue(plan.risk_level === '-' ? 'low' : plan.risk_level)
  };
});

const pendingActionRiskVariant = computed<'danger' | 'warning' | 'neutral'>(() => {
  const riskLevel = String(pendingActionPlan.value?.risk_level || 'low').toLowerCase();
  if (riskLevel === 'high') return 'danger';
  if (riskLevel === 'medium') return 'warning';
  return 'neutral';
});

const showHighRiskHint = computed(() => pendingActionRiskVariant.value === 'danger');

const requireDeleteKeywordConfirm = computed(() => {
  const toolName = String(pendingActionPlan.value?.tool_name || '').trim();
  return toolName === 'delete_case';
});

const canConfirmPendingAction = computed(() => {
  if (!requireDeleteKeywordConfirm.value) return true;
  return deleteActionConfirmText.value.toUpperCase() === 'DELETE';
});

const deleteConfirmSatisfied = computed(() => canConfirmPendingAction.value);

const pendingActionArgsEntries = computed(() => {
  const args = pendingActionPlan.value?.args;
  if (!args || typeof args !== 'object' || Array.isArray(args)) return [] as Array<{ key: string; value: string }>;
  return Object.entries(args)
    .slice(0, 10)
    .map(([key, value]) => ({ key: localizeActionFieldKey(key), value: toDisplayValue(value) }));
});

const pendingActionPreviewSummary = computed(() => {
  const preview = pendingActionPreview.value || {};
  const toolName = String(pendingActionPlan.value?.tool_name || '').trim();
  let keys = ['success', 'message', 'dry_run'];
  if (toolName === 'delete_case') {
    keys = ['success', 'message', 'case_id', 'title', 'status', 'deleted', 'dry_run'];
  } else if (toolName === 'list_cases') {
    keys = ['success', 'message', 'total', 'count'];
  } else if (toolName === 'generate_cases') {
    keys = ['success', 'message', 'count', 'use_rag'];
  }
  const entries: Array<{ key: string; value: string }> = [];
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(preview, key)) {
      entries.push({ key: localizeActionFieldKey(key), value: toDisplayValue(preview[key]) });
    }
  }
  // fallback for unknown tool output to avoid empty summary panel
  if (!entries.length) {
    const fallbackKeys = Object.keys(preview).slice(0, 8);
    for (const key of fallbackKeys) {
      entries.push({ key: localizeActionFieldKey(key), value: toDisplayValue(preview[key]) });
    }
  }
  return entries;
});

const pendingDeleteCasePreview = computed(() => {
  const toolName = String(pendingActionPlan.value?.tool_name || '').trim();
  const preview = pendingActionPreview.value || {};
  if (toolName !== 'delete_case') return null;
  if (!preview || typeof preview !== 'object' || Array.isArray(preview)) return null;
  const caseId = toDisplayValue(preview.case_id);
  const title = toDisplayValue(preview.title);
  const status = toDisplayValue(preview.status);
  if (caseId === '-' && title === '-' && status === '-') return null;
  return { caseId, title, status };
});

async function loadSessions(
  selectFirstIfNeeded = true,
  page = sessionPagination.value.page || 1,
  silent = false
) {
  const requestSeq = ++loadSessionsRequestSeq;
  try {
    if (!silent) {
      sessionLoading.value = true;
      sessionError.value = '';
    }
    const response = await listChatSessions({ page, per_page: sessionPagination.value.per_page });
    if (requestSeq !== loadSessionsRequestSeq) return;
    sessions.value = response.sessions;
    sessionPagination.value = response.pagination;
    if (silent) {
      // 静默刷新不应把当前会话从左侧列表“冲掉”
      ensureSessionVisible(currentSessionId.value, currentSessionTitle.value);
    }

    if (!currentSessionId.value && selectFirstIfNeeded && sessions.value.length > 0) {
      await selectSession(sessions.value[0].session_id, false);
    } else if (currentSessionId.value && !sessions.value.some((item) => item.session_id === currentSessionId.value)) {
      if (selectFirstIfNeeded) {
        if (sessions.value.length > 0) {
          await selectSession(sessions.value[0].session_id, false);
        } else {
          currentSessionId.value = '';
          currentSessionTitle.value = t('chat.sessions.defaultTitle');
          resetConversation();
        }
      }
    }
  } catch (error) {
    if (requestSeq !== loadSessionsRequestSeq) return;
    if (!silent) {
      sessionError.value = error instanceof Error ? error.message : t('chat.message.loadSessionsFailed');
    } else if (!notice.value) {
      setNotice('warning', error instanceof Error ? error.message : t('chat.message.loadSessionsFailed'));
    }
  } finally {
    if (!silent && requestSeq === loadSessionsRequestSeq) {
      sessionLoading.value = false;
    }
  }
}

async function loadHistory(sessionId: string, page = historyPagination.value.page || 1) {
  const requestSeq = ++loadHistoryRequestSeq;
  try {
    historyLoading.value = true;
    historyError.value = '';
    const response = await getChatHistory(sessionId, { page, per_page: historyPagination.value.per_page });
    if (requestSeq !== loadHistoryRequestSeq) return;
    messages.value = normalizeMessages(response.messages);
    restorePendingAction(messages.value);
    historyPagination.value = response.pagination;
    currentSessionTitle.value = findSessionTitle(sessionId);
    if (!messages.value.length) {
      suggestedQuestions.value = [];
      setNotice('info', t('chat.message.noHistory'));
    }
    await nextTick();
    scrollMessagesToBottom(false);
  } catch (error) {
    if (requestSeq !== loadHistoryRequestSeq) return;
    historyError.value = error instanceof Error ? error.message : t('chat.message.loadHistoryFailed');
    // 历史加载失败时保留当前已展示消息，避免将成功发送后的会话误显示为“空/失败”
    setNotice('warning', historyError.value);
  } finally {
    if (requestSeq === loadHistoryRequestSeq) {
      historyLoading.value = false;
    }
  }
}

async function selectSession(sessionId: string, reloadHistory = true) {
  abortActiveChat();
  currentSessionId.value = sessionId;
  currentSessionTitle.value = findSessionTitle(sessionId);
  historyPagination.value.page = 1;
  resetConversation();
  if (reloadHistory) {
    await loadHistory(sessionId, 1);
  }
}

async function handleNewSession() {
  try {
    const result = await createChatSession();
    const sessionId = result.session_id || result.session?.session_id || '';
    currentSessionId.value = sessionId;
    currentSessionTitle.value = result.session?.title || t('chat.sessions.defaultTitle');
    resetConversation();
    suggestedQuestions.value = [];
    ensureSessionVisible(sessionId, currentSessionTitle.value);
    void loadSessions(false, 1, true);
    setNotice('success', t('chat.message.newSessionReady'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.createSessionFailed'));
  }
}

const renamingSessionId = ref('');
const renameDraft = ref('');

function startRename(session: ChatSessionRecord) {
  renamingSessionId.value = session.session_id;
  renameDraft.value = session.title || '';
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
    const target = sessions.value.find((item) => item.session_id === sessionId);
    if (target) target.title = title;
    if (currentSessionId.value === sessionId) currentSessionTitle.value = title;
    cancelRename();
    setNotice('success', t('chat.message.renameSessionSuccess'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.renameSessionFailed'));
  } finally {
    sessionLoading.value = false;
  }
}

async function handleDeleteSession(sessionId: string) {
  if (!sessionId || sessionLoading.value) return;
  const target = sessions.value.find((item) => item.session_id === sessionId);
  pendingDeleteSessionId.value = sessionId;
  pendingDeleteSessionTitle.value = target?.title || t('chat.sessions.untitled');
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
      currentSessionTitle.value = t('chat.sessions.defaultTitle');
      resetConversation();
    }

    await loadSessions(true, sessionPagination.value.page);

    if (isCurrent && sessions.value.length > 0) {
      await selectSession(sessions.value[0].session_id, true);
    }
    setNotice('success', t('chat.message.deleteSessionSuccess'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.deleteSessionFailed'));
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

async function reloadCurrentHistory() {
  if (!currentSessionId.value) return;
  await loadHistory(currentSessionId.value, historyPagination.value.page);
}

async function changeSessionPage(page: number) {
  if (page < 1 || page > (sessionPagination.value.pages || 1)) return;
  await loadSessions(false, page);
}

async function changeHistoryPage(page: number) {
  if (!currentSessionId.value) return;
  if (page < 1 || page > (historyPagination.value.pages || 1)) return;
  await loadHistory(currentSessionId.value, page);
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

function isModelInitError(error: unknown) {
  if (!(error instanceof ApiError)) return false;
  const message = String(error.message || '').toLowerCase();
  const errorCode = String(error.errorCode || '').toUpperCase();
  return error.code === 503
    || errorCode === ErrorCodes.MODEL_NOT_INITIALIZED
    || errorCode === ErrorCodes.MODEL_SERVICE_UNAVAILABLE
    || message.includes('llm_not_initialized')
    || message.includes('chat model is not initialized')
    || message.includes('聊天模型尚未初始化')
    || message.includes('api key');
}

function resolveSendErrorMessage(error: unknown) {
  if (isModelInitError(error)) {
    return t('chat.message.llmNotInitialized');
  }

  if (error instanceof ApiError) {
    const errorCode = String(error.errorCode || '').toUpperCase();
    if (errorCode === ErrorCodes.MODEL_AUTH_FAILED || errorCode.includes('API_KEY')) {
      return t('chat.message.apiKeyInvalid');
    }
    if (errorCode === ErrorCodes.MODEL_RATE_LIMITED) {
      return t('chat.message.providerRateLimited');
    }
    if (errorCode === ErrorCodes.MODEL_TIMEOUT) {
      return t('chat.message.providerTimeout');
    }
    if (errorCode === ErrorCodes.MODEL_NETWORK_ERROR) {
      return t('chat.message.providerNetworkError');
    }
    const message = String(error.message || '').toLowerCase();
    if (message.includes('api key') || message.includes('apikey') || message.includes('配置异常')) {
      return t('chat.message.apiKeyInvalid');
    }
    return error.message || t('chat.message.sendFailed');
  }

  if (error instanceof Error) {
    return error.message || t('chat.message.sendFailed');
  }

  return t('chat.message.sendFailed');
}

async function handleSend() {
  const text = draftMessage.value.trim();
  if (!text || sendLoading.value) return;

  try {
    sendLoading.value = true;
    clearNotice();
    suggestedQuestions.value = [];
    resetPendingAction();

    if (!currentSessionId.value) {
      const created = await createChatSession({ title: text.slice(0, 32) });
      currentSessionId.value = created.session_id || created.session?.session_id || '';
      currentSessionTitle.value = created.session?.title || t('chat.sessions.defaultTitle');
    }
    ensureSessionVisible(currentSessionId.value, currentSessionTitle.value || text.slice(0, 32));

    const userKey = `user-${Date.now()}-${messageCounter.value += 1}`;
    messages.value.push({
      key: userKey,
      role: 'user',
      content: text,
      created_time: new Date().toISOString()
    });
    draftMessage.value = '';
    createPlaceholderAssistant();
    enableForceFollow(7000);
    await nextTick();
    scrollMessagesToBottom(true);

    const assistantIndex = messages.value.findIndex((item) => item.key === pendingAssistantKey.value);
    const requestPayload = {
      session_id: currentSessionId.value,
      message: text,
      mode: experimentalActionsEnabled.value ? 'action' : 'chat',
      type: 'chat' as const,
      use_context: true,
      use_knowledge: Boolean(chatConfig.value?.capabilities?.supports_knowledge),
      use_rag: Boolean(chatConfig.value?.capabilities?.supports_knowledge),
      auto_suggest: smartReplyEnabled.value,
      use_smart_reply: smartReplyEnabled.value,
      settings: {
        model: chatConfig.value?.default_model,
        max_tokens: chatConfig.value?.default_max_tokens,
        temperature: chatConfig.value?.default_temperature
      },
      require_confirmation: true,
      metadata: {}
    };

    if (experimentalActionsEnabled.value) {
      const result = await sendChatMessage(requestPayload);
      const actionStatus = String(result.status || '');
      const actionMessage = result.response || t('chat.state.emptyMessage');
      const toolName = String((result.action_plan as Record<string, unknown> | null)?.tool_name || '');
      const formattedContent = formatActionResultContent(
        actionMessage,
        actionStatus,
        toolName,
        result.tool_results || null
      );
      if (actionStatus === 'needs_confirmation' && result.execution_id) {
        pendingActionExecutionId.value = String(result.execution_id);
        pendingActionPlan.value = result.action_plan ?? null;
        pendingActionPreview.value = result.tool_results ?? null;
      }
      updateAssistantMessage(assistantIndex, formattedContent, {
        createdTime: result.timestamp || new Date().toISOString(),
        modelName: result.model_name || chatConfig.value?.default_model,
        pending: false,
        role: 'system'
      });
      await followOrNotifyNewMessage(true);
    } else if (streamEnabled.value) {
      abortActiveChat();
      const streamController = new AbortController();
      activeChatAbort = streamController;
      const streamSessionId = currentSessionId.value;
      const stream = await streamChatMessage(requestPayload, streamController.signal);
      let streamText = '';
      let streamTimestamp: string | undefined;
      let streamErrored = false;
      const modelName = chatConfig.value?.default_model || undefined;
      let lastFlushAt = 0;
      const flushIntervalMs = 50;
      let unreadMarked = false;

      const scheduleFlush = (force = false) => {
        if (currentSessionId.value !== streamSessionId) return;
        const now = Date.now();
        if (force || now - lastFlushAt >= flushIntervalMs) {
          if (streamFlushTimer !== null) {
            window.clearTimeout(streamFlushTimer);
            streamFlushTimer = null;
          }
          flushStreamUpdate(assistantIndex, streamText, streamTimestamp, modelName);
          lastFlushAt = now;
          return;
        }
        if (streamFlushTimer !== null) return;
        streamFlushTimer = window.setTimeout(() => {
          streamFlushTimer = null;
          flushStreamUpdate(assistantIndex, streamText, streamTimestamp, modelName);
          lastFlushAt = Date.now();
        }, flushIntervalMs);
      };

      for await (const event of stream) {
        if (streamController.signal.aborted || currentSessionId.value !== streamSessionId) break;
        if (event.type === 'error') {
          streamErrored = true;
          const statusCode = Number((event.raw as Record<string, unknown> | undefined)?.status_code || 0);
          const errorCode = String((event.raw as Record<string, unknown> | undefined)?.error_code || '');
          throw new ApiError(String(event.message || t('chat.message.sendFailed')), {
            code: Number.isFinite(statusCode) && statusCode > 0 ? statusCode : undefined,
            errorCode: errorCode || undefined,
            details: event.raw
          });
        }

        if (event.type === 'chunk') {
          streamText += String(event.content || '');
        }

        if (event.type === 'end') {
          if (event.full_response) {
            streamText = String(event.full_response);
          }
          streamTimestamp = event.timestamp || streamTimestamp;
          suggestedQuestions.value = Array.isArray(event.suggestions)
            ? event.suggestions.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
            : [];
        }

        scheduleFlush(event.type === 'end');
        const shouldMarkUnread = !unreadMarked && (event.type === 'chunk' || event.type === 'end');
        await followOrNotifyNewMessage(shouldMarkUnread);
        if (shouldMarkUnread && !autoScrollEnabled.value) {
          unreadMarked = true;
        }
      }

      if (streamFlushTimer !== null) {
        window.clearTimeout(streamFlushTimer);
        streamFlushTimer = null;
      }

      if (!streamErrored && assistantIndex >= 0) {
        updateAssistantMessage(assistantIndex, streamText, {
          createdTime: streamTimestamp,
          modelName: chatConfig.value?.default_model || undefined,
          pending: false
        });
      }
    } else {
      const result = await sendChatMessage(requestPayload);
      suggestedQuestions.value = Array.isArray(result.suggestions)
        ? result.suggestions.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
        : [];
      updateAssistantMessage(assistantIndex, result.response || t('chat.state.emptyMessage'), {
        createdTime: result.timestamp || new Date().toISOString(),
        modelName: result.model_name || chatConfig.value?.default_model,
        pending: false
      });
      await followOrNotifyNewMessage(true);
    }

    pendingAssistantKey.value = '';

    historyPagination.value.page = 1;
    // 后台静默刷新会话列表，不阻塞发送完成态与输入框可用性
    void loadSessions(false, 1, true);
    setNotice('success', t('chat.message.sendSuccess'));
  } catch (error) {
    if (isAbortError(error)) {
      pendingAssistantKey.value = '';
      return;
    }
    const assistantIndex = messages.value.findIndex((item) => item.key === pendingAssistantKey.value);
    const fallback = resolveSendErrorMessage(error);
    const modelInitError = isModelInitError(error);
    if (assistantIndex >= 0) {
      messages.value[assistantIndex] = {
        ...messages.value[assistantIndex],
        role: modelInitError ? 'system' : messages.value[assistantIndex].role,
        content: modelInitError ? t('chat.message.llmNotInitialized') : fallback,
        pending: false,
        model_name: chatConfig.value?.default_model || undefined
      };
    }
    pendingAssistantKey.value = '';
    setNotice(modelInitError ? 'warning' : 'danger', modelInitError ? t('chat.message.llmNotInitialized') : fallback);
  } finally {
    sendLoading.value = false;
  }
}

async function handleConfirmPendingAction() {
  if (!pendingActionExecutionId.value || sendLoading.value) return;
  if (!canConfirmPendingAction.value) {
    setNotice('warning', t('chat.action.deleteConfirmInvalid'));
    return;
  }
  try {
    sendLoading.value = true;
    const confirmMetadata: Record<string, unknown> = {
      operator_role: 'admin'
    };
    if (requireDeleteKeywordConfirm.value) {
      confirmMetadata.confirmation_text = deleteActionConfirmText.value;
      confirmMetadata.secondary_confirmed = canConfirmPendingAction.value;
    }
    const resp = await confirmExperimentalAction(pendingActionExecutionId.value, confirmMetadata);
    const toolName = String(pendingActionPlan.value?.tool_name || '');
    const output = asRecord(resp.tool_output);
    const content = formatActionResultContent(String(resp.message || '动作已确认执行'), 'confirmed', toolName, output);
    messages.value.push({
      key: `system-confirm-${Date.now()}-${messageCounter.value += 1}`,
      role: 'system',
      content,
      created_time: new Date().toISOString()
    });
    resetPendingAction();
    setNotice('success', t('chat.message.sendSuccess'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.sendFailed'));
  } finally {
    sendLoading.value = false;
  }
}

async function handleCancelPendingAction() {
  if (!pendingActionExecutionId.value || sendLoading.value) return;
  try {
    sendLoading.value = true;
    const resp = await cancelExperimentalAction(pendingActionExecutionId.value, 'cancel_from_chat_ui');
    messages.value.push({
      key: `system-cancel-${Date.now()}-${messageCounter.value += 1}`,
      role: 'system',
      content: String(resp.message || '动作已取消'),
      created_time: new Date().toISOString()
    });
    resetPendingAction();
    setNotice('warning', String(resp.message || '动作已取消'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.sendFailed'));
  } finally {
    sendLoading.value = false;
  }
}

async function handleSuggestionClick(suggestion: string) {
  const text = String(suggestion || '').trim();
  if (!text || sendLoading.value) return;
  void trackQuickReplyFeedback({
    suggestion_text: text,
    was_clicked: true,
    session_id: currentSessionId.value || undefined
  }).catch(() => undefined);
  draftMessage.value = text;
  await handleSend();
}

async function handleExport() {
  if (!currentSessionId.value) return;
  try {
    exportLoading.value = true;
    const result = await exportChatHistory(currentSessionId.value, 'json');
    const url = URL.createObjectURL(result.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename || 'chat_history.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setNotice('success', t('chat.message.exportSuccess'));
  } catch (error) {
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.exportFailed'));
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
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.templateLoadFailed'));
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
    setNotice('danger', error instanceof Error ? error.message : t('chat.message.clearSessionFailed'));
  }
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadSessions(false)]);
  await loadTemplatePreview(selectedTemplateType.value);
  // Enter-chat creates a local draft conversation only.
  // Persisted session is created when first message is sent.
  currentSessionId.value = '';
  currentSessionTitle.value = t('chat.sessions.defaultTitle');
  resetConversation();
});

watch(
  () => locale.value,
  async () => {
    await loadTemplatePreview(selectedTemplateType.value);
  }
);

onBeforeUnmount(() => {
  abortActiveChat();
  if (streamFlushTimer !== null) {
    window.clearTimeout(streamFlushTimer);
    streamFlushTimer = null;
  }
});
</script>

<style scoped>
.tp-chat-main-card:deep(.tp-card__body) {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-message-panel {
  position: relative;
  min-height: var(--tp-chat-message-min-height);
  max-height: max(220px, calc(var(--tp-chat-message-max-height) - 140px));
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.chat-message-panel::-webkit-scrollbar {
  width: 8px;
}

.chat-message-panel::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--tp-color-text-500) 35%, transparent);
  border-radius: 999px;
}

.chat-message-list {
  display: grid;
  gap: 14px;
}

.chat-jump-latest {
  position: sticky;
  bottom: 10px;
  margin-left: auto;
  z-index: 3;
}

.chat-assistant-card {
  width: 100%;
  max-width: min(760px, 100%);
  min-width: 0;
  padding: 16px 18px;
  border-radius: var(--tp-radius-lg);
  border: 1px solid var(--tp-border-default);
  background: var(--tp-bg-subtle);
}

.tp-chat-session__delete {
  min-width: 56px;
}

.tp-chat-session {
  width: 100%;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  overflow: visible;
}

.tp-chat-session__main {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.tp-chat-session__actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-self: end;
}

.chat-assistant-card--system {
  background: var(--tp-bg-subtle);
  background: color-mix(in srgb, var(--tp-color-warning-500) 8%, var(--tp-bg-surface));
}

.chat-meta {
  color: var(--tp-color-text-500);
}

.tp-chat-template-panel {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-md);
  padding: 10px 12px;
  background: var(--tp-bg-subtle);
}

.tp-chat-template-select {
  min-width: 220px;
}

.tp-chat-template-preview {
  border: 1px dashed var(--tp-border-default);
  border-radius: var(--tp-radius-sm);
  padding: 8px 10px;
  background: var(--tp-bg-surface);
  color: var(--tp-color-text-600);
  max-height: 120px;
  overflow: auto;
  white-space: pre-wrap;
}

.tp-chat-action-panel {
  border: 1px dashed var(--tp-border-default);
  border-radius: var(--tp-radius-sm);
  padding: 8px 10px;
  background: var(--tp-bg-subtle);
}

.tp-chat-action-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 4px 8px;
  align-items: start;
}

.tp-chat-action-grid > span {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.tp-chat-action-preview {
  margin: 0;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 12px;
  color: var(--tp-color-text-600);
}

.tp-chat-action-delete-preview {
  border: 1px solid var(--tp-border-default);
  border-radius: var(--tp-radius-sm);
  padding: 8px 10px;
  background: var(--tp-surface-raised);
}

.tp-chat-action-delete-preview__title {
  font-weight: 600;
  color: var(--tp-color-danger-600);
}

.tp-chat-action-risk-hint {
  border-left: 3px solid var(--tp-color-danger-500);
  background: var(--tp-bg-subtle);
  background: color-mix(in srgb, var(--tp-color-danger-500) 8%, transparent);
  padding: 6px 8px;
  border-radius: var(--tp-radius-xs);
  color: var(--tp-color-danger-700);
}

.tp-chat-composer-footer {
  align-items: flex-start;
  gap: 12px;
}

.tp-chat-toggle-group {
  flex: 1 1 560px;
  min-width: min(100%, 420px);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.tp-chat-switch {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-bg-surface) 90%, var(--tp-color-text-100) 10%);
  cursor: pointer;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.tp-chat-switch__input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.tp-chat-switch__track {
  width: 44px;
  height: 26px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tp-color-text-300) 86%, transparent);
  border: 1px solid var(--tp-border-default);
  position: relative;
  flex: 0 0 auto;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.tp-chat-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tp-bg-surface);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.18);
  transition: transform 0.2s ease;
}

.tp-chat-switch__text {
  line-height: 1.35;
  overflow-wrap: anywhere;
  color: var(--tp-color-text-700);
  font-size: 13px;
}

.tp-chat-switch__state {
  min-width: 34px;
  text-align: center;
  color: var(--tp-color-text-500);
  font-size: 11px;
  line-height: 1;
  font-weight: 700;
  padding: 4px 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--tp-color-text-300) 70%, transparent);
  background: color-mix(in srgb, var(--tp-color-text-200) 60%, transparent);
}

.tp-chat-switch__state--on {
  color: var(--tp-color-primary-700);
  border-color: color-mix(in srgb, var(--tp-color-primary-500) 60%, transparent);
  background: color-mix(in srgb, var(--tp-color-primary-500) 20%, transparent);
}

.tp-chat-switch--on {
  background: color-mix(in srgb, var(--tp-color-primary-500) 10%, var(--tp-bg-surface) 90%);
}

.tp-chat-switch--on .tp-chat-switch__track {
  background: var(--tp-color-primary-500);
  border-color: var(--tp-color-primary-600);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--tp-color-primary-500) 24%, transparent);
}

.tp-chat-switch--on .tp-chat-switch__thumb {
  transform: translateX(18px);
}

.tp-chat-switch__input:focus-visible + .tp-chat-switch__track {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tp-color-primary-500) 20%, transparent);
}

.tp-chat-switch--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tp-chat-composer-actions {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.tp-chat-empty-state {
  padding: 10px 12px;
  border-radius: var(--tp-radius-sm);
  background: var(--tp-bg-subtle);
  border: 1px solid var(--tp-border-default);
  text-align: left;
}

.tp-chat-empty-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.tp-chat-empty-list > li {
  margin: 0;
}

.tp-chat-empty-question {
  width: 100%;
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--tp-color-primary-500) 36%, var(--tp-border-default));
  border-radius: 999px;
  padding: 7px 12px;
  margin: 0;
  color: var(--tp-color-primary-700);
  background: color-mix(in srgb, var(--tp-color-primary-500) 10%, var(--tp-surface-raised));
  font-size: 13px;
  line-height: 1.35;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.12s ease;
}

.tp-chat-empty-question:hover {
  background: color-mix(in srgb, var(--tp-color-primary-500) 18%, var(--tp-surface-raised));
  border-color: color-mix(in srgb, var(--tp-color-primary-500) 60%, var(--tp-border-default));
}

.tp-chat-empty-question:active {
  transform: translateY(1px);
}

.tp-chat-empty-question:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .tp-chat-action-grid {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .tp-chat-toggle-group {
    grid-template-columns: 1fr;
    min-width: 0;
  }

  .tp-chat-composer-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
