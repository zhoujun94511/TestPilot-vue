export default {
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
    hint: 'Click save to apply your changes immediately'
  },
  section: {
    shared: 'Shared settings',
    sharedHint: 'Settings shared across multiple models',
    providers: 'Model groups',
    providerHint: '{provider} specific settings',
    sharedScopeHint: 'Shared options are listed below; provider sections appear when keys are scoped to a vendor.',
    active: 'Active'
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
    textareaPlaceholder: 'Please enter multiline content'
  },
  state: {
    loadingCategories: 'Loading categories...',
    loadingItems: 'Loading configuration items...',
    noCategorySelected: 'Please select a category',
    noChanges: 'No unsaved changes',
    pendingChanges: '{count} unsaved change(s)',
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
    unsavedChangesConfirm: 'There are unsaved changes in the current category. Switching categories will discard them. Continue?',
    apiKeyCleared: '{provider} API key cleared',
    apiKeyClearFailed: 'Failed to clear API key'
  },
  audit: {
    title: 'Recent config changes',
    loading: 'Loading change logs...',
    empty: 'No change logs yet',
    change: 'Old: {oldValue} -> New: {newValue}'
  }
};
