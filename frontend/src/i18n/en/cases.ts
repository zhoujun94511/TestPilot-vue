export default {
  page: {
    title: 'Test Cases',
    subtitle: 'Bring the core case workflow into Vue and validate list, filters, generation, batch actions, export, and stats'
  },
  tabs: {
    generate: 'Case Generation',
    manage: 'Case Management'
  },
  actions: {
    generate: 'Generate Cases',
    hideGenerate: 'Hide Generator',
    batchGenerate: 'Batch Generate',
    hideBatchGenerate: 'Hide Batch Form',
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
    title: 'Single Generation',
    hint: 'Enter a requirement description to generate test cases',
    autoPriorityHint: 'Priority will be determined automatically'
  },
  batch: {
    title: 'Batch Generation',
    hint: 'Enter multiple requirements, one per line, to generate case sets',
    requirementsLabel: 'Requirement List',
    requirementsPlaceholder: 'Enter multiple requirements, one per line',
    processModeLabel: 'Process Mode',
    processHint: 'The backend supports sequential or parallel processing'
  },
  form: {
    requirementLabel: 'Requirement Description',
    requirementPlaceholder: 'Enter a requirement, business rule, or testing target',
    caseCountLabel: 'Case Count',
    caseCountOption: '{count} items',
    categoryLabel: 'Case Category',
    categoryAll: 'All Categories',
    useRag: 'Use knowledge-base enhancement',
    useRagDisabled: 'Knowledge-base enhancement is unavailable right now; generation will use the model only'
  },
  filters: {
    title: 'Search & Filters',
    keywordLabel: 'Keyword',
    keywordPlaceholder: 'Search by title, description, or case ID',
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
      regenerate: 'Regenerate',
      exportOne: 'Export',
      deleteOne: 'Delete'
    }
  },
  stats: {
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
    statsFailed: 'Failed to load statistics',
    configFailed: 'Failed to load case config',
    requirementRequired: 'Please enter a requirement before generating',
    requirementsRequired: 'Please enter at least one requirement before batch generation'
  },
  pagination: {
    pageInfo: 'Page {page} / {pages}, {total} total'
  }
};
