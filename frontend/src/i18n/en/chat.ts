export default {
  page: {
    title: 'AI Chat Assistant',
    subtitle: 'Finish the session and message loop first, then layer in enhancements'
  },
  actions: {
    newSession: 'New Session',
    refresh: 'Refresh',
    export: 'Export History',
    exporting: 'Exporting',
    send: 'Send',
    sending: 'Sending',
    jumpToLatest: '{count} new messages, jump to latest',
    deleteSession: 'Delete',
    renameSession: 'Rename',
    clearSession: 'Clear Session',
    insertTemplate: 'Insert Template',
    confirmAction: 'Confirm Action',
    cancelAction: 'Cancel Action'
  },
  sessions: {
    title: 'Sessions',
    count: '{count} sessions',
    emptyTitle: 'No sessions yet',
    emptyMessage: 'Click "New Session" to start a conversation',
    untitled: 'Untitled Session',
    defaultTitle: 'AI Chat Assistant',
    emptyPreview: 'No preview',
    currentId: 'Current Session',
    noSessionSelected: 'No session selected yet'
  },
  composer: {
    label: 'Message',
    placeholder: 'Type your question. Enter to send, Shift+Enter for a new line',
    hint: 'Streaming is enabled and responses appear in real time',
    streamToggle: 'Enable streaming response',
    smartReplyToggle: 'Enable smart suggestions',
    templateToggle: 'Enable prompt templates',
    experimentalActionsToggle: 'Enable experimental actions'
  },
  state: {
    loadingSessions: 'Loading sessions...',
    loadingHistory: 'Loading history...',
    emptyTitle: 'No messages yet',
    emptyMessage: 'Select a session or send your first message to begin',
    welcomeLead: 'Hello! I am your AI testing assistant, and I can help answer testing-related questions.',
    welcomePrompt: 'You can try asking me:',
    starters: {
      caseDesignReview: 'How should I run test case design and review effectively?',
      testStrategy: 'How should I create a practical test strategy?',
      defectAnalysis: 'How do I analyze and localize defects efficiently?',
      automation: 'How should I approach test automation?',
      performance: 'How should I plan and execute performance testing?'
    },
    thinking: 'AI is thinking...'
  },
  metrics: {
    tokens: '{count} tokens'
  },
  message: {
    loadSessionsFailed: 'Failed to load sessions',
    loadHistoryFailed: 'Failed to load history',
    sendFailed: 'Failed to send message',
    llmNotInitialized: 'Chat model is not ready. Check provider and API key in Config Center, then retry.',
    apiKeyInvalid: 'API key is invalid or missing. Update it in Config Center or .env, then retry.',
    providerRateLimited: 'Provider rate limit or quota exceeded. Please retry later.',
    providerTimeout: 'Provider request timed out. Please retry later.',
    providerNetworkError: 'Failed to connect to provider service. Check network or endpoint settings.',
    sendSuccess: 'Message sent',
    newSessionReady: 'New session created',
    createSessionFailed: 'Failed to create session',
    noHistory: 'This session has no history yet',
    exportSuccess: 'Chat history export started',
    exportFailed: 'Failed to export chat history',
    clearSessionConfirm: 'Clear all messages in current session? This action cannot be undone.',
    clearSessionSuccess: 'Current session cleared',
    clearSessionFailed: 'Failed to clear session',
    templateInserted: 'Template inserted into composer',
    templateEmpty: 'Template is empty',
    templateLoadFailed: 'Failed to load template',
    deleteSessionConfirm: 'Delete session "{title}"? This action cannot be undone.',
    deleteSessionSuccess: 'Session deleted',
    deleteSessionFailed: 'Failed to delete session',
    renameSessionSuccess: 'Session renamed',
    renameSessionFailed: 'Failed to rename session',
    renameSessionEmpty: 'Session name cannot be empty',
    experimentalToggleSuccess: 'Experimental actions setting updated',
    experimentalToggleFailed: 'Failed to update experimental actions setting'
  },
  roles: {
    user: 'You',
    assistant: 'AI',
    system: 'System'
  },
  modelStatus: {
    configError: 'Configuration error',
    serviceUnavailable: 'Service unavailable',
    connectionFailed: 'Connection failed',
    unknownModel: 'Unknown model'
  },
  history: {
    title: 'History'
  },
  template: {
    title: 'Templates',
    placeholder: 'Templates and settings are reserved for a later pass',
    selectLabel: 'Prompt Template',
    loading: 'Loading template...',
    empty: 'No template content',
    types: {
      testStrategy: 'Test Strategy Consultation',
      caseReview: 'Test Case Review Advice',
      bugAnalysis: 'Bug Analysis Guidance',
      automationAdvice: 'Automation Advice',
      performanceTest: 'Performance Test Guidance'
    }
  },
  setting: {
    title: 'Settings',
    placeholder: 'Reserved for a later enhancement'
  },
  export: {
    title: 'Export'
  },
  richContent: {
    copy: 'Copy',
    copied: 'Copied',
    copyFailed: 'Copy failed',
    expand: 'Expand',
    collapse: 'Collapse',
    tableHint: 'Wide table: scroll horizontally to view more'
  },
  messageCount: '{count} messages',
  quickReply: {
    title: 'Suggested follow-ups',
    stats: '{total} suggested / {clicked} clicked / CTR {rate}'
  },
  action: {
    pendingTitle: 'Pending action confirmation',
    executionId: 'Execution ID',
    plan: 'Action plan',
    intent: 'Intent',
    tool: 'Tool',
    risk: 'Risk',
    args: 'Arguments',
    preview: 'Dry-run preview',
    deletePreviewTitle: 'Target to delete (dry-run)',
    highRiskHint: 'High-risk action: confirming will execute the operation.',
    deleteConfirmLabel: 'Type DELETE for second confirmation',
    deleteConfirmPlaceholder: 'Enter DELETE to enable confirm',
    deleteConfirmInvalid: 'Please type DELETE before confirming',
    deleteConfirmReady: 'Second confirmation passed, ready to confirm',
    deleteConfirmPending: 'Waiting for second confirmation (type DELETE)',
    field: {
      success: 'Success',
      message: 'Message',
      caseId: 'Case ID',
      title: 'Title',
      status: 'Status',
      deleted: 'Will delete',
      dryRun: 'Dry run',
      total: 'Total',
      count: 'Count',
      useRag: 'Use RAG'
    }
  }
};
