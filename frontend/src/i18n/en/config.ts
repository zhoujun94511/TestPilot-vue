export default {
  toolbar: {
    backendHint: 'If categories fail to load, ensure the backend is running, then use Refresh in the sidebar or panel header.'
  },
  page: {
    title: 'Config Center',
    subtitle: 'Manage AI models, test-case generation, and runtime settings'
  },
  category: {
    title: 'Categories',
    loading: 'Loading categories...',
    empty: 'No categories available',
    selectHint: 'Select a category to view settings',
    current: 'Current category'
  },
  panel: {
    title: 'Configuration Items',
    loading: 'Loading configuration items...',
    empty: 'This category has no configuration items',
    hint: 'Takes effect after save'
  },
  section: {
    shared: 'Shared settings',
    sharedHint: 'Settings shared across multiple models',
    providers: 'Model groups',
    providerHint: '{provider} specific settings',
    sharedScopeHint: 'Shared options are listed below; provider sections appear when keys are scoped to a vendor.',
    active: 'Active',
    tokenBudget: 'Token request limits',
    tokenBudgetHint: 'Per-request max_tokens: Chat, quick replies, and Ollama use the chat limit; case generation and requirement analysis use each vendor row.',
    tokenBudgetProviderHint: 'Case generation and requirement analysis',
    tokenSessionGuard: 'Session token guardrails',
    tokenSessionGuardHint: 'In-process TokenMonitor caps; breaching them blocks further LLM calls. Changes apply after save under Performance.'
  },
  actions: {
    save: 'Save',
    export: 'Export',
    exporting: 'Exporting',
    import: 'Import',
    importing: 'Importing',
    reload: 'Reload',
    clearValue: 'Clear Value',
    saving: 'Saving'
  },
  form: {
    key: 'Key',
    value: 'Value',
    description: 'Description',
    valueType: 'Value Type',
    updatedAt: 'Updated At',
    dirty: 'Modified',
    enabled: 'Enabled',
    disabled: 'Disabled',
    selectPlaceholder: 'Please select',
    textPlaceholder: 'Please enter',
    numberPlaceholder: 'Please enter a number',
    passwordPlaceholder: 'Please enter secret',
    textareaPlaceholder: 'Please enter multiline content',
    dedupWeights: {
      valueType: 'Weights (0–1)',
      title: 'Title weight',
      steps: 'Steps weight',
      expected: 'Expected result weight',
      preconditions: 'Preconditions weight'
    }
  },
  state: {
    loadingCategories: 'Loading categories...',
    loadingItems: 'Loading configuration items...',
    noCategorySelected: 'Please select a category',
    noChanges: '',
    pendingChanges: '{count} unsaved',
    validationRunning: 'Validating configuration'
  },
  message: {
    saved: 'Configuration saved',
    savedWithWarnings: 'Configuration saved, but some items did not pass validation',
    saveFailed: 'Failed to save configuration',
    loadFailed: 'Failed to load configuration',
    exportReady: 'Configuration exported',
    exportFailed: 'Failed to export configuration',
    importReady: 'Imported {count} configuration item(s)',
    importFailed: 'Failed to import configuration',
    validationPassed: 'Validation passed',
    validationFailed: 'Validation failed',
    validationRequestFailed: 'Validation request failed',
    noChangesToSave: 'No changes to save',
    unsavedChangesTitle: 'Unsaved changes',
    unsavedChangesConfirm: 'There are unsaved changes in the current category. Switching categories will discard them. Continue?',
    apiKeyCleared: '{provider} API key cleared',
    apiKeyClearFailed: 'Failed to clear API key'
  },
  audit: {
    title: 'Recent config changes',
    subtitle: 'Read-only trail; entries appear after you save or reset settings',
    navDescription: 'Review changes from saves and reloads',
    loading: 'Loading change logs...',
    empty: 'No change logs yet',
    change: 'Old: {oldValue} -> New: {newValue}'
  }
};
