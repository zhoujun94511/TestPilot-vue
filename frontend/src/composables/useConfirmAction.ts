import { reactive } from 'vue';

export type ConfirmVariant = 'primary' | 'danger' | 'warning';

export interface OpenConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  onConfirm: () => void | Promise<void>;
}

export type ConfirmActionHandle = {
  visible: boolean;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  variant: ConfirmVariant;
  open: (options: OpenConfirmOptions) => void;
  handleConfirm: () => Promise<void>;
  handleCancel: () => void;
  clearPending: () => void;
};

/**
 * 确认弹窗状态。返回 reactive 对象，供模板 `confirm.visible` / `v-model="confirm.visible"` 正确解包。
 * （勿用 plain object + ref，否则嵌套 ref 在模板中不会 unwrap，会出现空白遮罩卡死。）
 */
export function useConfirmAction(defaultCancelText = ''): ConfirmActionHandle {
  let pendingConfirm: (() => void | Promise<void>) | null = null;

  const dialog = reactive({
    visible: false,
    title: '',
    message: '',
    confirmText: '',
    cancelText: defaultCancelText,
    variant: 'primary' as ConfirmVariant,

    open(options: OpenConfirmOptions) {
      if (!String(options.title || '').trim()) {
        return;
      }
      dialog.title = options.title;
      dialog.message = options.message;
      dialog.confirmText = options.confirmText?.trim() || options.title;
      if (options.cancelText) {
        dialog.cancelText = options.cancelText;
      }
      dialog.variant = options.variant ?? 'primary';
      pendingConfirm = options.onConfirm;
      dialog.visible = true;
    },

    clearPending() {
      pendingConfirm = null;
    },

    handleCancel() {
      dialog.visible = false;
      pendingConfirm = null;
    },

    async handleConfirm() {
      const action = pendingConfirm;
      pendingConfirm = null;
      dialog.visible = false;
      if (action) {
        await action();
      }
    }
  });

  return dialog;
}
