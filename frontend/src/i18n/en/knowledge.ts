export default {
  page: {
    title: 'Knowledge Base',
    subtitle: 'Upload, search, maintain, and rebuild the RAG knowledge base'
  },
  tabs: {
    upload: 'Knowledge Upload',
    files: 'Knowledge File Management'
  },
  actions: {
    upload: 'Upload File',
    hideUpload: 'Hide Upload',
    refresh: 'Refresh',
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
  filters: {
    title: 'Filter & Search',
    keywordLabel: 'Search Keyword',
    keywordPlaceholder: 'Enter file name, description, or keywords',
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
    category: 'File Category',
    categoryPlaceholder: 'Select a category',
    description: 'File Description',
    descriptionPlaceholder: 'Add a short note for this file',
    submit: 'Start Upload',
    empty: 'Please select file(s) first',
    dragHint: 'Select multiple files at once. The system will parse and ingest them automatically.',
    progress: 'Upload Progress',
    filesSelected: '{count} files selected'
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
    selectAll: 'Select All',
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
  pagination: {
    pageInfo: 'Page {page} / {pages}'
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
