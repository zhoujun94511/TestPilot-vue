export default {
  page: {
    title: 'Test Cases'
  },
  tabs: {
    generate: 'Case Generation',
    manage: 'Case Management'
  },
  actions: {
    generate: 'Generate Cases',
    batchGenerate: 'Batch Generate',
    export: 'Export',
    exporting: 'Exporting',
    exportExcel: 'Excel',
    exportCsv: 'CSV',
    exportJson: 'JSON',
    downloadTemplate: 'Download Template',
    templateDownloading: 'Downloading Template',
    generating: 'Generating',
    batchGenerating: 'Batch Generating',
    deleteSelected: 'Delete Selected',
    clearInput: 'Clear'
  },
  single: {
    title: 'Single Generation'
  },
  batch: {
    title: 'Batch Generation',
    requirementsPlaceholder: 'Login checks; refund flow',
    requirementsHelper: 'Separate requirements with ;'
  },
  state: {
    generatingTitle: 'Generating test cases',
    batchGeneratingTitle: 'Batch generation in progress',
    batchGeneratingHint: 'Generating one requirement at a time. Each finished requirement is saved immediately. Keep this page open.',
    batchGeneratingProgress: '{done}/{total} requirements finished, {saved} cases saved.'
  },
  form: {
    requirementLabel: 'Requirement',
    requirementPlaceholder: 'e.g. Login must validate account state and show errors',
    caseCountLabel: 'Case Count',
    caseCountOption: '{count} items'
  },
  filters: {
    title: 'Search & Filters',
    keywordLabel: 'Keyword',
    keywordPlaceholder: 'Search',
    priorityLabel: 'Priority',
    priorityAll: 'All priorities',
    statusLabel: 'Status',
    statusAll: 'All statuses',
    categoryLabel: 'Category',
    categoryAll: 'All categories',
    apply: 'Search',
    selectedCount: '{count} selected',
    selectedAll: 'All {count} selected'
  },
  table: {
    title: 'Case list',
    empty: 'No test cases yet',
    loading: 'Loading test cases...',
    noSteps: 'No steps yet',
    stepsPreview: '{count} steps, first: {sample}',
    columns: {
      caseId: 'Case ID',
      title: 'Title',
      priority: 'Priority',
      status: 'Status',
      category: 'Category',
      testMethod: 'Test Method',
      module: 'Module',
      tags: 'Tags',
      steps: 'Step Preview',
      updatedAt: 'Updated At',
      actions: 'Actions'
    },
    actions: {
      edit: 'Edit',
      regenerate: 'Regenerate',
      exportOne: 'Export',
      deleteOne: 'Delete'
    }
  },
  edit: {
    title: 'Edit test case',
    loading: 'Loading case details…',
    noCase: 'No case selected',
    descriptionLabel: 'Description',
    preconditionLabel: 'Preconditions',
    stepsLabel: 'Test steps',
    expectedLabel: 'Expected results',
    linesHelper: 'One item per line',
    tagsHelper: 'Separate multiple tags with commas',
    tagsPlaceholder: 'e.g. home, mobile',
    stepsRequired: 'Add at least one step and one expected result'
  },
  stats: {
    title: 'Statistics',
    loading: 'Loading statistics...',
    empty: 'No statistics available',
    emptyHint: 'There are no statistics to display yet',
    total: 'Total Cases',
    draft: 'Draft',
    active: 'Active',
    deprecated: 'Deprecated',
    priorityDistribution: 'Priority Distribution',
    categoryDistribution: 'Category Distribution',
    emptyDistribution: 'No distribution data yet'
  },
  confirm: {
    generateTitle: 'Confirm case generation',
    generateMessage: 'Generate {count} test cases from the current requirement?',
    batchGenerateTitle: 'Confirm batch generation',
    batchGenerateMessage: 'Generate {count} requirements one by one? Each finished requirement is saved immediately.',
    regenerateTitle: 'Confirm regeneration',
    regenerateMessage: 'Regenerate test cases based on "{title}"?',
    deleteTitle: 'Confirm deleting test case',
    deleteMessage: 'Delete "{title}"? This action cannot be undone.',
    deleteBatchTitle: 'Confirm deleting selected test cases',
    deleteBatchMessage: 'Delete {count} selected test cases? This action cannot be undone.'
  },
  message: {
    loadFailed: 'Failed to load test case list',
    refreshSuccess: 'Case data refreshed',
    generateSuccess: '{count} test cases generated',
    generateFailed: 'Failed to generate test cases',
    batchGenerateSuccess: 'Batch generation finished, {count} test cases created',
    batchGeneratePartial: '{saved} cases were saved. {failed} requirements failed. Saved cases are kept.',
    batchGenerateFailed: 'Failed to batch generate test cases',
    generateSynced: 'Synced to Case Management for filtering and export',
    batchGenerateSynced: 'Batch results synced to Case Management for filtering and export',
    exportSuccess: 'Export started',
    exportFailed: 'Failed to export test cases',
    templateDownloadSuccess: 'Template download started',
    templateDownloadFailed: 'Failed to download template',
    deleteSuccess: 'Test case deleted',
    deleteFailed: 'Failed to delete test case',
    deleteBatchSuccess: '{count} test cases deleted',
    deleteBatchPartial: 'Partial success: {success} deleted, {failed} failed',
    deleteBatchFailed: 'Failed to delete selected test cases',
    updateSuccess: 'Test case saved',
    updateFailed: 'Failed to save test case',
    statsFailed: 'Failed to load statistics',
    configFailed: 'Failed to load case config',
    requirementRequired: 'Please enter a requirement before generating',
    requirementsRequired: 'Please enter at least one requirement before batch generation'
  }
};
