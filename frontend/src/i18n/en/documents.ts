export default {
  page: {
    title: 'Document Analysis',
    subtitle: 'Upload requirement documents, analyze them, and generate test cases from results'
  },
  tabs: {
    upload: 'Document Upload',
    manage: 'Document & Requirement Management'
  },
  actions: {
    upload: 'Upload Document',
    hideUpload: 'Hide Upload',
    backToDocuments: 'Back to Documents',
    analyzeCurrent: 'Analyze Current',
    reanalyze: 'Reanalyze',
    refresh: 'Refresh List',
    generateCases: 'Generate Test Cases',
    exportRequirements: 'Export Requirements',
    exportingRequirements: 'Exporting Requirements',
    analyzing: 'Analyzing',
    generating: 'Generating',
    uploading: 'Uploading',
    deleteDocuments: 'Delete Documents',
    deleteRequirements: 'Delete Requirements',
    selectAllRequirements: 'Select All Requirements',
    viewResult: 'View Result',
    preview: 'Preview'
  },
  filters: {
    title: 'Search & Filters',
    keywordLabel: 'Keyword',
    keywordPlaceholder: 'Search by document name, content, or keyword',
    analysisTypeLabel: 'Analysis Type',
    apply: 'Search'
  },
  form: {
    useRag: 'Use Knowledge Base Enhancement',
    useRagDisabled: 'Knowledge base enhancement is unavailable, pure model generation will be used'
  },
  upload: {
    title: 'Document Upload',
    file: 'Choose Document',
    fileHint: 'Supported: TXT / CSV / DOCX / PDF / JSON / MD / XLSX / YAML',
    analysisType: 'Default Analysis Type',
    empty: 'Please choose a document before uploading',
    autoAnalyzeHint: 'Auto-analyze after upload and open result page',
    autoAnalyzeToggle: 'Auto-analyze after upload and open results'
  },
  table: {
    title: 'Document List',
    empty: 'No documents yet',
    loading: 'Loading document list...',
    columns: {
      name: 'Name',
      type: 'Type',
      status: 'Status',
      updatedAt: 'Updated At',
      actions: 'Actions'
    }
  },
  analysis: {
    title: 'Analysis Results',
    showPanel: 'Show Analysis Results',
    hidePanel: 'Hide Analysis Results',
    empty: 'No analysis results yet',
    loading: 'Analyzing document...',
    error: 'Analysis failed',
    summaryTitle: 'Analysis Overview',
    requirementsTitle: 'Extracted Requirements',
    noRequirements: 'No requirements were extracted from the current result',
    sourceDocument: 'Source Document',
    currentDocument: 'Current Document'
  },
  preview: {
    title: 'Document Preview',
    empty: 'No preview available',
    loading: 'Loading document preview...',
    truncated: 'Content truncated',
    meta: 'Type: {type} · Size: {size}'
  },
  history: {
    title: 'Parsed Requirement History',
    subtitle: 'Browse and manage all persisted requirement analysis results',
    loading: 'Loading parsed requirements...',
    empty: 'No parsed requirements yet',
    source: 'Source Document',
    sourceAll: 'All Source Documents',
    selectedRequirementsCount: '{count} requirements selected (cross-page)',
    searchPlaceholder: 'Search by req id/title/content',
    typeAll: 'All Types',
    priorityAll: 'All Priorities'
  },
  result: {
    title: 'Analysis Summary',
    requirementsCount: 'Requirements',
    testPointsCount: 'Test Points',
    businessRulesCount: 'Business Rules',
    totalCount: 'Total',
    selected: 'Selected Document',
    selectedDocumentsCount: '{count} documents selected (cross-page)'
  },
  requirement: {
    id: 'ID',
    title: 'Title',
    type: 'Type',
    priority: 'Priority',
    category: 'Category'
  },
  message: {
    loadFailed: 'Failed to load document list',
    refreshSuccess: 'Document list refreshed',
    uploadSuccess: 'Document uploaded successfully',
    uploadFailed: 'Failed to upload document',
    analyzeSuccess: 'Document analyzed successfully',
    analyzeFailed: 'Failed to analyze document',
    generateSuccess: 'Test case generation triggered',
    generateFailed: 'Failed to generate test cases',
    exportRequirementsSuccess: 'Requirements export started',
    exportRequirementsFailed: 'Failed to export requirements',
    selectDocumentFirst: 'Please select a document first',
    noAnalysisResult: 'No analysis result is available for test case generation',
    searchFailed: 'Search failed',
    loadAnalysisFailed: 'Failed to load analysis result',
    previewFailed: 'Failed to load document preview',
    noDocumentSelection: 'Please select documents to delete',
    noRequirementSelection: 'Please select requirements to delete',
    resultNotReady: 'No analysis result is available for this document yet. Please run analysis first.',
    resultLoadedFromHistory: 'Loaded historical analysis results for this document',
    deleteDocumentSuccess: 'Documents deleted successfully',
    deleteRequirementSuccess: 'Requirements deleted successfully',
    deleteDocumentsPartial: 'Partial document deletion (success: {success}, failed: {failed})',
    deleteRequirementsPartial: 'Partial requirement deletion (success: {success}, failed: {failed})',
    previewCopySuccess: 'Preview content copied',
    previewCopyFailed: 'Failed to copy preview content'
  },
  confirm: {
    generateCases: 'Generate test cases from the current analysis result?',
    batchGenerateTitle: 'Batch Generation Confirmation',
    batchGenerateByRequirementsMessage: 'Batch generate: process {reqCount} requirements (3 each, about {caseCount} cases). Continue?',
    batchGenerateByDocumentsMessage: 'Batch generate: {count} docs, {reqCount} requirements (about {caseCount} cases), skipped {skippedCount} unanalyzed. Continue?',
    deleteDocuments: 'Delete selected documents? This action cannot be undone.',
    deleteRequirements: 'Delete selected requirements? This action cannot be undone.'
  },
  pagination: {
    pageInfo: 'Page {page} / {pages}'
  }
};
