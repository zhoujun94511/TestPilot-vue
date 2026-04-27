/// <reference types="vite/client" />

declare global {
  interface Window {
    __TESTPILOT_BASE_PATH__?: string;
  }
}

export {};

