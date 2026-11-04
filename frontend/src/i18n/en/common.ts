export default {
  app: {
    brand: 'TestPilot',
    subtitle: 'AI test case generation'
  },
  nav: {
    dashboard: 'Dashboard',
    configCenter: 'Config Center',
    knowledgeBase: 'Knowledge Base',
    documents: 'Documents',
    documentHistory: 'Requirement History',
    chat: 'AI Chat',
    experimentalTools: 'Experimental tools',
    cases: 'Test Cases'
  },
  shell: {
    pageKicker: 'Enterprise AI Testing',
    mainNav: 'Main navigation',
    breadcrumb: 'Breadcrumb',
    collapseSidebar: 'Collapse sidebar',
    expandSidebar: 'Expand sidebar',
    openMenu: 'Open menu',
    logout: 'Sign out',
    account: 'Account',
    signedInAs: 'Signed in as {name}',
    closeMenu: 'Close menu',
    switchToChinese: '切换到中文',
    switchToEnglish: 'Switch to English',
    switchToDark: 'Switch to Dark Mode',
    switchToLight: 'Switch to Light Mode',
    groups: {
      overview: 'Overview',
      analysis: 'Analysis',
      generation: 'Generation',
      assistant: 'AI Assistant',
      system: 'System'
    },
    theme: {
      light: 'Light Theme',
      dark: 'Dark Theme',
      lightShort: 'Light',
      darkShort: 'Dark'
    },
    system: {
      busy: 'System Busy',
      ready: 'System Ready'
    },
    sidebarFooter: 'Sidebar footer',
    sidebarCopyright: '© {yearRange} {brand}. All rights reserved.'
  },
  language: {
    label: 'Language',
    zhCn: 'Simplified Chinese',
    en: 'English',
    zhShort: '简体',
    enShort: 'EN',
    unsupportedTraditional: 'Only Simplified Chinese and English are supported (no Traditional Chinese locale).'
  },
  actions: {
    save: 'Save',
    refresh: 'Refresh',
    chooseFile: 'Choose File',
    upload: 'Upload',
    analyze: 'Analyze',
    generate: 'Generate',
    loading: 'Loading',
    retry: 'Retry',
    cancel: 'Cancel',
    close: 'Close',
    copy: 'Copy Content',
    copied: 'Copied',
    delete: 'Delete',
    edit: 'Edit',
    confirm: 'Confirm',
    expand: 'View failure details',
    collapse: 'Hide details',
    previous: 'Previous',
    next: 'Next',
    more: 'More'
  },
  toolbar: {
    selectedCount: '{count} selected',
    clearSelection: 'Clear selection'
  },
  pagination: {
    range: 'Items {start}–{end} of {total}'
  },
  status: {
    loading: 'Loading',
    empty: 'No data',
    error: 'Load failed',
    healthy: 'Healthy',
    warning: 'Warning',
    unhealthy: 'Unhealthy',
    connected: 'Connected',
    disconnected: 'Disconnected',
    noData: 'No data'
  },
  boolean: {
    yes: 'Yes',
    no: 'No'
  },
  feedback: {
    success: 'Success',
    warning: 'Please check your input',
    info: 'Notice'
  },
  tokenSession: {
    statusLoaded: 'Token session status updated',
    warningTokens:
      'Session token usage is at {tokenPercent}% ({tokenUsed}/{tokenMax}), nearing the {warnPercent}% guardrail. Adjust max tokens per session in Config Center or restart the backend to reset.',
    warningCalls:
      'Session LLM calls are at {callPercent}% ({callUsed}/{callMax}), nearing the {warnPercent}% guardrail. Adjust max calls per session in Config Center or restart the backend to reset.',
    exceededTokens:
      'Session token budget exhausted ({used}/{limit}). Raise the limit in Config Center or restart the backend, then retry.',
    exceededCalls:
      'Session LLM call limit reached ({used}/{limit}). Raise the limit in Config Center or restart the backend, then retry.'
  },
  errors: {
    requestFailed: 'Request failed. Please try again.',
    network: 'Network error. Check your connection or backend service.',
    http401: 'Not signed in or session expired',
    http403: 'You do not have permission for this action',
    http404: 'The requested resource was not found',
    http408: 'Request timed out. Please try again.',
    http429: 'Too many requests. Please try again later.',
    http4xx: 'Request could not be completed ({status})',
    http5xx: 'Service temporarily unavailable ({status})'
  }
};
