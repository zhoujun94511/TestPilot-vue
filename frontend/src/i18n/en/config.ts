export default {
  page: {
    title: 'Config Center'
  },
  category: {
    title: 'Categories',
    selectHint: 'Select a category to view settings'
  },
  panel: {
    title: 'Configuration Items',
    loading: 'Loading configuration items...',
    empty: 'This category has no configuration items'
  },
  section: {
    shared: 'Shared settings',
    providers: 'Model groups',
    providerHint: '{provider} specific settings',
    active: 'Active',
    tokenBudget: 'Token request limits',
    tokenSessionGuard: 'Session token guardrails'
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
    noChangesToSave: 'No changes to save',
    unsavedChangesTitle: 'Unsaved changes',
    unsavedChangesConfirm: 'There are unsaved changes in the current category. Switching categories will discard them. Continue?',
    apiKeyCleared: '{provider} API key cleared',
    apiKeyClearFailed: 'Failed to clear API key'
  },
  audit: {
    title: 'Recent config changes',
    navDescription: 'Review changes from saves and reloads',
    loading: 'Loading change logs...',
    empty: 'No change logs yet',
    change: 'Old: {oldValue} -> New: {newValue}'
  }
};
