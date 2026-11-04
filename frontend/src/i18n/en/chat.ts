export default {
  page: {
    title: 'AI Chat Assistant',
    subtitle: 'Finish the session and message loop first, then layer in enhancements'
  },
  toolbar: {
    noSessionHint: 'Create or select a session to refresh, export, or clear messages.',
    backendUnavailableHint: 'If sessions fail to load, check the backend connection, then try New session or Retry in the sidebar.'
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
    draftTitle: 'New chat',
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
    templateToggle: 'Enable prompt templates'
  },
  experimentalTools: {
    openStandaloneHint: 'Opened Case generation with the requirement prefilled. Review the fields, then generate.',
    toolLabel: 'Tool',
    run: 'Run tool',
    running: 'Running…',
    queryAudit: '[{tool}] from experimental tools page',
    validationFailed: 'Fill required fields before running',
    runSuccess: 'Tool run finished',
    runSkipped: 'Tool was not executed (check args or permissions)',
    runFailed: 'Tool run failed',
    risk: {
      low: 'Low risk',
      medium: 'Medium risk',
      high: 'High risk',
      unknown: 'Risk unknown'
    },
    errors: {
      explicitRequired: 'Tool name missing or invalid. Pick a tool and fill the form.',
      unknownTool: 'Tool "{tool}" is not registered on the server. Check deploy version and experimentalTools config.',
      featureDisabled: 'Experimental actions are disabled. Set ENABLE_EXPERIMENTAL_ACTIONS=true on the server.',
      rateLimited: 'Too many experimental tool requests. Please wait and retry.'
    },
    fields: {
      limit: 'Max items per group',
      requirement_text: 'Requirement text',
      requirement_id: 'Requirement',
      case_count: 'Max model additions',
      use_llm: 'Let the model add business steps the rules miss'
    },
    tools: {
      rule_skeleton_cases: 'Rule skeleton preview',
      ac_coverage_review: 'Acceptance coverage review',
      trace_matrix: 'Requirement–case traceability'
    },
    toolDesc: {
      rule_skeleton_cases:
        'For search, login and form scenarios, rules first write the empty, not-found, special-character, overlong and repeat cases; the model only fills what the rules miss. Preview first; nothing is saved until you confirm.',
      ac_coverage_review:
        'Splits a requirement into acceptance points and checks them against the cases linked to it, listing coverage, gaps and step-structure problems. Read-only.',
      trace_matrix:
        'Lists requirements with no cases, cases pointing to missing requirements, and cases with no requirement. Read-only.'
    },
    placeholders: {
      limit: 'Default 50, max 200',
      requirement_text: 'e.g. Users search products from the search box; keywords up to 50 characters…',
      requirement_id: 'No requirement (optional)',
      requirement_id_required: 'Select a requirement',
      case_count: 'Default 5, max 10'
    }
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
    actionModeNotSupported:
      'Chat no longer supports mode=action. Use Experimental tools in the sidebar, or POST /api/experimental-actions/execute with tool_name and args.',
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
    experimentalToggleFailed: 'Failed to update experimental actions setting',
    experimentalActionsConfigDesc: 'Enable experimental action runtime'
  },
  toolMarkdown: {
    genericActionSuccess: 'Action executed successfully',
    genericOperationSuccess: 'Operation succeeded',
    actionConfirmed: 'Action confirmed and executed',
    actionCancelled: 'Action cancelled',
    priority: 'Priority',
    steps: 'Steps',
    expectedResult: 'Expected result',
    covers: 'Acceptance point',
    listTruncated: 'Showing first {shown} of {total} items',
    none: 'None',
    scenarios: 'Detected scenarios',
    scenario: {
      search: 'Search',
      login: 'Login',
      form: 'Form'
    },
    ruleCases: 'Written by rules ({count})',
    llmCases: 'Added by the model ({count})',
    requirement: 'Requirement',
    linkedCases: 'Linked cases',
    noCriteria: 'No acceptance points could be split out of the requirement text.',
    criterion: 'Acceptance point',
    coverageState: 'State',
    covered: 'Covered',
    gap: 'Gap',
    matchedCase: 'Matched case',
    score: 'Overlap',
    structureIssues: 'Structure to fix ({count})',
    issue: {
      title_too_short: 'Title too short',
      steps_missing: 'No steps',
      steps_too_few: 'Only one step',
      steps_vague: 'Vague step',
      expected_missing: 'No expected result'
    },
    trace: {
      requirementsWithoutCases: 'Requirements with no cases ({count})',
      casesWithMissingRequirement: 'Cases pointing to a missing requirement ({count})',
      casesUnlinked: 'Cases with no requirement ({count})',
      requirementsWithCases: 'Requirements with cases ({count}, fewest first)',
      caseCount: '{count} cases'
    }
  },
  roles: {
    user: 'You',
    assistant: 'AI Assistant',
    system: 'System'
  },
  modelStatus: {
    configError: 'Configuration error',
    serviceUnavailable: 'Service unavailable',
    connectionFailed: 'Connection failed',
    unknownModel: 'Unknown model'
  },
  toolMeta: {
    status: 'Status',
    tool: 'Tool',
    total: 'Total',
    hits: 'Hits',
    searchStatus: 'Search status',
    generated: 'Generated',
    rag: 'RAG'
  },
  history: {
    title: 'History'
  },
  template: {
    title: 'Templates',
    placeholder: 'Choose a template and insert it into the message box.',
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
    stats: '{total} suggested / {clicked} clicked / CTR {rate}',
    statsHint: '{count} in this batch',
    statsGlobal: '{clicks} total clicks · {users} tracked users'
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
