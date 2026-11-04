export default {
  page: {
    title: '知识库管理',
    subtitle: '上传、搜索、维护并重建 RAG 知识库'
  },
  tabs: {
    upload: '知识库上传',
    files: '知识库文件管理',
    search: '知识检索'
  },
  toolbar: {
    filesLead: '维护向量库文件；选中后可批量删除，索引异常时可重建。'
  },
  banner: {
    vectorDisabledTitle: '向量库功能已关闭',
    vectorDisabledMessage:
      '当前 ENABLE_VECTOR_STORE 为关闭，知识库相关接口（含文件列表、统计、上传、检索与索引重建）均不可用。请在配置中心开启后保存，并刷新本页。',
    vectorDisabledAction: '打开配置中心',
    vectorDisabledStateTitle: '知识库暂不可用',
    vectorDisabledStateMessage:
      '向量库关闭时后端会拒绝全部知识库 API。开启 ENABLE_VECTOR_STORE 并刷新后，方可浏览文件、上传与检索。'
  },
  actions: {
    upload: '上传文件',
    refresh: '刷新',
    rebuild: '重建索引',
    search: '搜索',
    delete: '删除',
    batchDelete: '批量删除',
    deleting: '删除中',
    uploading: '上传中',
    rebuilding: '重建中',
    preview: '预览',
    closeResults: '关闭'
  },
  searchPage: {
    threshold: '相似度阈值',
    openInFiles: '在文件管理中打开'
  },
  filters: {
    title: '筛选与检索',
    subtitle: '按关键词、分类与状态筛选知识库文件',
    keywordLabel: '搜索关键词',
    keywordPlaceholder: '搜索',
    categoryLabel: '分类',
    categoryAll: '全部分类',
    statusLabel: '状态',
    statusAll: '全部状态',
    apply: '应用筛选'
  },
  upload: {
    title: '上传知识文件',
    file: '选择文件（可多选）',
    fileHint: '支持 TXT / CSV / DOCX / PDF / JSON / MD',
    serverHint: '单文件不超过 {size}；允许类型：{types}',
    category: '文件分类',
    categoryPlaceholder: '请选择分类',
    description: '文件描述',
    descriptionPlaceholder: '为文件补充说明',
    submit: '开始上传',
    empty: '请先选择文件',
    dragHint: '可一次选择多个文件，上传后系统将自动解析并入库',
    progress: '上传进度',
    filesSelected: '已选择 {count} 个文件'
  },
  edit: {
    title: '编辑文件信息',
    empty: '未选择文件',
    success: '文件信息已更新',
    failed: '更新文件信息失败'
  },
  preview: {
    title: '文档预览',
    loading: '正在加载预览...',
    empty: '请选择文件进行预览',
    failed: '加载预览失败',
    noContent: '暂无可预览内容',
    metaType: '类型: {type}',
    metaSize: '大小: {size}',
    truncated: '内容已截断'
  },
  stats: {
    title: '统计信息',
    totalFiles: '文件总数',
    totalChunks: '文档块数',
    storageSize: '存储大小',
    lastUpdate: '最近更新时间',
    indexStatus: '索引状态',
    vectorEnabled: '向量库状态',
    vectorOn: '已开启',
    vectorOff: '已关闭',
    categoryDistribution: '分类分布',
    indexReady: '已构建',
    indexEmpty: '待构建'
  },
  table: {
    title: '文件列表',
    empty: '暂无知识库文件',
    loading: '正在加载文件列表...',
    selectAll: '全选',
    columns: {
      name: '名称',
      category: '分类',
      type: '类型',
      size: '大小',
      chunks: '块数',
      status: '状态',
      updatedAt: '更新时间',
      actions: '操作'
    }
  },
  result: {
    title: '语义搜索结果',
    empty: '暂无匹配结果',
    loading: '正在搜索知识库...',
    score: '相似度',
    source: '来源',
    relevance: '相关性',
    snippet: '内容片段'
  },
  confirm: {
    deleteSelected: '确认删除选中的知识库文件吗？',
    rebuild: '确认重建索引吗？该操作可能会耗时较长。'
  },
  message: {
    loadFailed: '加载知识库失败',
    refreshSuccess: '刷新成功',
    statsFailed: '加载统计信息失败',
    searchFailed: '搜索失败',
    uploadSuccess: '上传成功',
    uploadFailed: '上传失败',
    uploadPartialFailed: '部分文件上传失败',
    uploadDuplicate: '文件已存在，已复用现有记录',
    deleteSuccess: '删除成功',
    deleteFailed: '删除失败',
    rebuildSuccess: '重建成功',
    rebuildFailed: '重建失败',
    selectFileFirst: '请先选择文件',
    noSelection: '请选择要删除的文件',
    batchDeleteFailed: '批量删除失败',
    validateFailed: '校验失败',
    previewCopySuccess: '预览内容已复制',
    previewCopyFailed: '复制预览内容失败'
  },
  category: {
    test_cases: '测试用例',
    requirements: '需求文档',
    business_rules: '业务规则',
    best_practices: '最佳实践',
    templates: '模板资料',
    other: '其他'
  },
  status: {
    active: '已启用',
    processing: '处理中',
    archived: '已归档',
    failed: '失败',
    duplicate: '重复'
  }
};
