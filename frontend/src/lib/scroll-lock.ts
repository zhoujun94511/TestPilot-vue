/** 多层 Sheet/Dialog 叠加时引用计数，避免提前解锁 */
let scrollLockDepth = 0;

const LOCK_CLASS = 'tp-modal-scroll-lock';

export function lockDocumentScroll() {
  scrollLockDepth += 1;
  if (scrollLockDepth === 1) {
    document.documentElement.classList.add(LOCK_CLASS);
  }
}

export function unlockDocumentScroll() {
  scrollLockDepth = Math.max(0, scrollLockDepth - 1);
  if (scrollLockDepth === 0) {
    document.documentElement.classList.remove(LOCK_CLASS);
  }
}
