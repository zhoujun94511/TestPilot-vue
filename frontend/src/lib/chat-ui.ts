import { cva, type VariantProps } from 'class-variance-authority';
import { interactiveFocusRingClass } from '@/lib/focus-ui';
import { cn } from '@/lib/utils';

/** Chat 侧栏会话行（勿与 shell navItemClass 叠用：nav 为 flex，会与会话 grid 冲突） */
export const chatSessionItemClass = cva(
  cn(
    'box-border grid w-full min-w-0 cursor-pointer grid-cols-1 gap-2 rounded-[var(--tp-radius-md)] border px-3 py-2.5',
    'no-underline transition-[background-color,border-color,color,transform] duration-150',
    interactiveFocusRingClass
  ),
  {
    variants: {
      active: {
        true: cn(
          'border border-[color-mix(in_srgb,var(--tp-color-primary-600)_22%,var(--tp-border-default))]',
          'border-l-[3px] border-l-[var(--tp-color-primary-600)]',
          'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_11%,var(--tp-bg-surface))]',
          'text-[var(--tp-color-text-900)]'
        ),
        false: cn(
          'border-[var(--tp-border-default)] border-l-[3px] border-l-[var(--tp-border-default)]',
          'bg-[var(--tp-bg-surface)] text-[var(--tp-color-text-600)]',
          'hover:border-[var(--tp-border-strong)] hover:border-l-[var(--tp-border-strong)]',
          'hover:bg-[var(--tp-bg-subtle)] hover:text-[var(--tp-color-text-900)]'
        )
      }
    },
    defaultVariants: { active: false }
  }
);

export type ChatSessionItemClassOptions = VariantProps<typeof chatSessionItemClass>;

export const chatSessionMainClass = 'min-w-0 grid gap-0.5';

export const chatSessionActionsClass =
  'flex min-w-0 flex-wrap items-center justify-end gap-1.5';

export const chatSessionDeleteBtnClass = 'min-w-14';

export const chatMetaClass = 'text-[var(--tp-color-text-500)]';

export const chatComposerShellClass = cn(
  'mt-auto shrink-0 border-t border-[var(--tp-border-default)] pt-[var(--tp-space-3)]',
  'bg-[color-mix(in_srgb,var(--tp-bg-surface)_96%,transparent)]'
);

export const chatTemplatePanelClass =
  'mb-2 rounded-[var(--tp-radius-md)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-2.5 px-3';

export const chatTemplateSelectClass = 'min-w-[220px]';

export const chatTemplatePreviewClass =
  'mt-2 max-h-[120px] overflow-auto whitespace-pre-wrap rounded-[var(--tp-radius-sm)] border border-dashed border-[var(--tp-border-default)] bg-[var(--tp-bg-surface)] p-2 px-2.5 text-[var(--tp-color-text-600)]';

export const chatActionPanelClass =
  'mt-2 rounded-[var(--tp-radius-sm)] border border-dashed border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-2 px-2.5';

export const chatActionGridClass =
  'grid grid-cols-[120px_1fr] items-start gap-x-2 gap-y-1 max-sm:grid-cols-1 max-sm:gap-y-0.5 [&>span]:min-w-0 [&>span]:break-words';

export const chatActionPreviewClass =
  'm-0 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-[var(--tp-color-text-600)]';

export const chatActionDeletePreviewClass =
  'mb-2 rounded-[var(--tp-radius-sm)] border border-[var(--tp-border-default)] bg-[var(--tp-surface-raised)] p-2 px-2.5';

export const chatActionDeletePreviewTitleClass =
  'font-semibold text-[var(--tp-color-danger-600)]';

export const chatActionRiskHintClass = cn(
  'mb-2 rounded-[var(--tp-radius-xs)] border-l-[3px] border-l-[var(--tp-color-danger-500)] p-1.5 px-2',
  'bg-[color-mix(in_srgb,var(--tp-color-danger-500)_8%,transparent)] text-[var(--tp-color-danger-700)]'
);

export const chatComposerFooterClass =
  'mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2';

export const chatToggleGroupClass =
  'flex min-w-0 flex-1 flex-nowrap items-center gap-x-3 max-lg:flex-wrap';

export const chatComposerActionsClass =
  'flex flex-[0_0_auto] flex-wrap justify-end gap-2 max-sm:w-full max-sm:justify-end';

export const chatEmptyStateClass =
  'mt-4 rounded-[var(--tp-radius-sm)] border border-[var(--tp-border-default)] bg-[var(--tp-bg-subtle)] p-2.5 px-3 text-left';

export const chatEmptyListClass = 'mt-2 grid list-none gap-2 p-0';

export const chatSessionListClass = 'grid gap-2';

export const chatMainCardClass = cn(
  'flex h-full flex-col',
  '[&>div:last-child]:flex [&>div:last-child]:min-h-0 [&>div:last-child]:flex-1 [&>div:last-child]:flex-col'
);

export const chatMainCardHeaderClass =
  'flex flex-wrap items-start justify-between gap-2';

export const chatMessagePanelClass =
  'chat-message-panel mb-2 min-h-0 flex-1';

/** 历史分页在滚动区外，避免贴底被 max-height 裁切 */
export const chatHistoryPagerClass =
  'mb-2 shrink-0 border-t border-[var(--tp-border-default)] pt-2';

export const chatMessageListClass = 'grid gap-[var(--tp-page-block-gap)]';

/** 用户消息气泡（右侧） */
export const chatUserBubbleClass = cn(
  'max-w-full rounded-[1.125rem] rounded-br-[var(--tp-radius-sm)] px-3.5 py-2.5',
  'border border-[color-mix(in_srgb,var(--tp-color-primary-600)_24%,var(--tp-border-default))]',
  'bg-[color-mix(in_srgb,var(--tp-color-primary-600)_14%,var(--tp-bg-surface))]',
  'text-[var(--tp-color-text-900)] shadow-[var(--tp-shadow-sm)]'
);

/** 助手消息气泡（左侧，与头像并列） */
export const chatAssistantBubbleClass = cn(
  'max-w-full rounded-[1.125rem] rounded-bl-[var(--tp-radius-sm)] px-3.5 py-2.5',
  'border border-[color-mix(in_srgb,var(--tp-color-ai-600)_18%,var(--tp-border-default))]',
  'bg-[color-mix(in_srgb,var(--tp-color-ai-600)_9%,var(--tp-bg-subtle))]',
  'text-[var(--tp-color-text-900)] shadow-[var(--tp-shadow-sm)]'
);

export const chatAssistantBubbleSystemClass = cn(
  chatAssistantBubbleClass,
  'border-[color-mix(in_srgb,var(--tp-color-warning-500)_28%,var(--tp-border-default))]',
  'bg-[color-mix(in_srgb,var(--tp-color-warning-500)_10%,var(--tp-bg-surface))]'
);

export const chatMessageColumnClass = 'flex max-w-[min(640px,100%)] min-w-0 flex-col gap-1';

export const chatAssistantColumnClass =
  'flex min-w-0 max-w-[min(760px,100%)] flex-1 flex-col gap-1';

export const chatMessageFootMetaClass =
  'px-0.5 text-xs leading-snug text-[var(--tp-color-text-500)] [overflow-wrap:anywhere]';

/** @deprecated use chatUserBubbleClass */
export const chatUserCardClass = chatUserBubbleClass;

/** @deprecated use chatAssistantBubbleClass */
export const chatAssistantCardClass = cn(chatAssistantColumnClass, chatAssistantBubbleClass);

/** @deprecated use chatAssistantBubbleSystemClass */
export const chatAssistantCardSystemClass = chatAssistantBubbleSystemClass;

export const chatJumpLatestButtonClass =
  'chat-jump-latest sticky bottom-2.5 z-[3] ml-auto';

export function chatMessageRowClass(role: string) {
  return cn(
    'flex gap-2.5',
    role === 'user' ? 'justify-end' : 'justify-start',
    role === 'assistant' && 'items-start'
  );
}

export const chatAssistantAvatarClass = 'mt-0.5 shrink-0';

export const chatUserAvatarClass = 'mt-0.5 shrink-0';

export const chatMessageMetaClass =
  'text-sm leading-snug text-[var(--tp-color-text-500)]';

/** 在消息滚动区外、输入框上方，避免被 .chat-message-panel 的 max-height 裁切 */
export const chatSuggestionsClass = cn(
  'chat-suggestions shrink-0 border-t border-[var(--tp-border-default)] px-0.5 pt-3 pb-1'
);

export const chatSuggestionsHeaderClass = cn(
  chatMessageMetaClass,
  'mb-2 flex items-center justify-between gap-2'
);

export const chatSuggestionsActionsClass = 'flex flex-wrap gap-2';

export const chatEmptyQuestionClass = cn(
  'm-0 w-full cursor-pointer appearance-none rounded-full border px-3 py-[7px] text-left text-[13px] leading-snug',
  'border-[color-mix(in_srgb,var(--tp-color-primary-500)_36%,var(--tp-border-default))]',
  'bg-[color-mix(in_srgb,var(--tp-color-primary-500)_10%,var(--tp-surface-raised))] text-[var(--tp-color-primary-700)]',
  'transition-[background-color,border-color,transform] duration-200 hover:border-[color-mix(in_srgb,var(--tp-color-primary-500)_60%,var(--tp-border-default))] hover:bg-[color-mix(in_srgb,var(--tp-color-primary-500)_18%,var(--tp-surface-raised))] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60'
);
