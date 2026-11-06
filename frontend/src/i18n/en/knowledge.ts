export default {
  page: {
    title: 'Knowledge Base'
  },
  tabs: {
    upload: 'Knowledge Upload',
    files: 'Knowledge File Management',
    search: 'Knowledge Search'
  },
  banner: {
    vectorDisabledTitle: 'Vector store is disabled',
    vectorDisabledMessage:
      'ENABLE_VECTOR_STORE is off. All knowledge APIs (file list, stats, upload, search, and index rebuild) are blocked. Enable it in Config Center, save, and refresh this page.',
    vectorDisabledAction: 'Open Config Center',
    vectorDisabledStateTitle: 'Knowledge base unavailable',
    vectorDisabledStateMessage:
      'With the vector store off, the backend rejects every knowledge API. Enable ENABLE_VECTOR_STORE and refresh to browse files, upload, and search.'
  },
  actions: {
    upload: 'Upload File',
    rebuild: 'Rebuild Index',
    search: 'Search',
    delete: 'Delete',
    batchDelete: 'Batch Delete',
    deleting: 'Deleting',
    uploading: 'Uploading',
    rebuilding: 'Rebuilding',
    preview: 'Preview',
    closeResults: 'Close'
  },
  searchPage: {
    threshold: 'Similarity Threshold',
    openInFiles: 'Open in file management'
  },
  filters: {
    title: 'Filter & Search',
    keywordLabel: 'Search Keyword',
    keywordPlaceholder: 'Search',
    categoryLabel: 'Category',
    categoryAll: 'All Categories',
    statusLabel: 'Status',
    statusAll: 'All Statuses',
    apply: 'Apply Filters'
  },
  upload: {
    title: 'Upload Knowledge File',
    file: 'Choose File(s)',
    fileHint: 'Supported: TXT / CSV / DOCX / PDF / JSON / MD',
    serverHint: 'Max {size} per file; allowed types: {types}',
    category: 'File Category',
    categoryPlaceholder: 'Select a category',
    description: 'File Description',
    descriptionPlaceholder: 'Add a short note for this file',
    submit: 'Start Upload',
    empty: 'Please select file(s) first',
    progress: 'Upload Progress',
    filesSelected: '{count} files selected'
  },
  edit: {
    title: 'Edit file metadata',
    empty: 'No file selected',
    success: 'File metadata updated',
    failed: 'Failed to update file metadata'
  },
  preview: {
    title: 'Document Preview',
    loading: 'Loading preview...',
    empty: 'Select a file to preview',
    failed: 'Failed to load preview',
    noContent: 'No preview content available',
    metaType: 'Type: {type}',
    metaSize: 'Size: {size}',
    truncated: 'Content truncated'
  },
  stats: {
    title: 'Statistics',
    totalFiles: 'Total Files',
    totalChunks: 'Document Chunks',
    storageSize: 'Storage Size',
    lastUpdate: 'Last Updated',
    indexStatus: 'Index Status',
    vectorEnabled: 'Vector Store',
    vectorOn: 'Enabled',
    vectorOff: 'Disabled',
    categoryDistribution: 'Category Distribution',
    indexReady: 'Built',
    indexEmpty: 'Not Built'
  },
  table: {
    title: 'File List',
    empty: 'No knowledge files yet',
    loading: 'Loading file list...',
    columns: {
      name: 'Name',
      category: 'Category',
      type: 'Type',
      size: 'Size',
      chunks: 'Chunks',
      status: 'Status',
      updatedAt: 'Updated At',
      actions: 'Actions'
    }
  },
  result: {
    title: 'Semantic Search Results',
    empty: 'No matches found',
    loading: 'Searching the knowledge base...',
    score: 'Similarity',
    source: 'Source',
    relevance: 'Relevance',
    snippet: 'Snippet'
  },
  confirm: {
    deleteSelected: 'Delete the selected knowledge files?',
    rebuild: 'Rebuild the index now? This may take a while.'
  },
  message: {
    loadFailed: 'Failed to load knowledge base',
    refreshSuccess: 'Refreshed successfully',
    statsFailed: 'Failed to load statistics',
    searchFailed: 'Search failed',
    uploadSuccess: 'Upload successful',
    uploadFailed: 'Upload failed',
    uploadPartialFailed: 'Some files failed to upload',
    uploadDuplicate: 'The file already exists and the existing record was reused',
    deleteSuccess: 'Deleted successfully',
    deleteFailed: 'Delete failed',
    rebuildSuccess: 'Rebuild successful',
    rebuildFailed: 'Rebuild failed',
    selectFileFirst: 'Please select a file first',
    noSelection: 'Please select files to delete',
    batchDeleteFailed: 'Batch delete failed',
    validateFailed: 'Validation failed',
    previewCopySuccess: 'Preview content copied',
    previewCopyFailed: 'Failed to copy preview content'
  },
  category: {
    test_cases: 'Test Cases',
    requirements: 'Requirements',
    business_rules: 'Business Rules',
    best_practices: 'Best Practices',
    templates: 'Templates',
    other: 'Other'
  },
  status: {
    active: 'Active',
    processing: 'Processing',
    archived: 'Archived',
    failed: 'Failed',
    duplicate: 'Duplicate'
  }
};
