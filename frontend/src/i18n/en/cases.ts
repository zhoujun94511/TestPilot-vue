export default {
  page: {
    title: 'Test Cases',
    subtitle: 'Bring the core case workflow into Vue and validate list, filters, generation, batch actions, export, and stats'
  },
  tabs: {
    generate: 'Case Generation',
    manage: 'Case Management'
  },
  generateMode: {
    aria: 'Generation mode'
  },
  toolbar: {
    manageLead: 'Review stats and the case list; export and templates live under More.',
    exportMenu: 'Export & template'
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
    refresh: 'Refresh',
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
    requirementsHelper: 'For multiple items, split each requirement with ;',
    processModeLabel: 'Process mode',
    processModeHelper: 'Sequential: one by one; parallel: concurrent'
  },
  state: {
    generatingTitle: 'Generating test cases',
    generatingHint: 'The model is analyzing your requirement and saving cases. This often takes tens of seconds to a few minutes—please keep this page open.',
    batchGeneratingTitle: 'Batch generation in progress',
    batchGeneratingHint: 'Cases are being generated per requirement (sequential or parallel). Duration depends on count and whether RAG is enabled.'
  },
  form: {
    requirementLabel: 'Requirement',
    requirementPlaceholder: 'e.g. Login must validate account state and show errors',
    requirementHelper: 'Be specific on scope or acceptance; priority is inferred',
    caseCountLabel: 'Case Count',
    caseCountOption: '{count} items',
    ragFollowsConfigOn: 'Knowledge enhancement is on. Change it in Config Center.',
    ragFollowsConfigOff: 'Knowledge enhancement is off. Change it in Config Center.',
    ragUnavailable: 'Knowledge base is off. Generation uses the model only.'
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
    selectedCount: '{count} selected'
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
    totalHint: 'From the case list',
    statusHint: 'Grouped by status',
    priorityDistribution: 'Priority Distribution',
    categoryDistribution: 'Category Distribution',
    emptyDistribution: 'No distribution data yet'
  },
  confirm: {
    generateTitle: 'Confirm case generation',
    generateMessage: 'Generate {count} test cases from the current requirement?',
    batchGenerateTitle: 'Confirm batch generation',
    batchGenerateMessage: 'Process {count} requirements with {mode} mode?',
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
