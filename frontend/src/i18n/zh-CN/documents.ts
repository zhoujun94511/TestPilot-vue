export default {
  page: {
    title: '需求文档分析'
  },
  tabs: {
    upload: '需求文档上传',
    manage: '需求文档与需求管理',
    history: '需求历史'
  },
  actions: {
    upload: '上传文档',
    backToDocuments: '返回文档分析',
    analyzeCurrent: '分析当前',
    reanalyze: '重新分析',
    generateCases: '生成测试用例',
    exportRequirements: '导出需求',
    exportingRequirements: '导出需求中',
    analyzing: '分析中',
    generating: '生成中',
    generatingProgress: '已完成 {done}/{total}，已入库 {saved}',
    uploading: '上传中',
    deleteDocuments: '删除文档',
    deleteRequirements: '删除需求',
    selectAllRequirements: '全选需求',
    viewResult: '查看结果',
    preview: '预览'
  },
  filters: {
    title: '搜索与筛选',
    keywordLabel: '关键词',
    keywordPlaceholder: '搜索',
    analysisTypeLabel: '分析类型',
    apply: '搜索'
  },
  upload: {
    title: '文档上传',
    file: '选择文档',
    fileHint: '支持 TXT / CSV / DOCX / PDF / JSON / MD / XLSX / YAML',
    analysisType: '默认分析类型',
    empty: '请选择一个文档后再上传',
    autoAnalyzeToggle: '上传后自动分析并打开结果'
  },
  table: {
    title: '文档列表',
    empty: '暂无需求文档',
    loading: '正在加载文档列表...',
    columns: {
      name: '名称',
      type: '类型',
      status: '状态',
      updatedAt: '更新时间',
      actions: '操作'
    }
  },
  analysis: {
    title: '分析结果',
    showPanel: '查看分析结果',
    hidePanel: '收起分析结果',
    empty: '暂无分析结果',
    loading: '正在分析文档...',
    error: '分析失败',
    summaryTitle: '分析概览',
    requirementsTitle: '提取出的需求',
    noRequirements: '当前结果中未提取到需求项',
    sourceDocument: '来源文档',
    currentDocument: '当前文档'
  },
  preview: {
    title: '文档预览',
    empty: '暂无预览内容',
    loading: '正在加载文档预览...',
    truncated: '内容已截断',
    meta: '类型: {type} · 大小: {size}'
  },
  history: {
    title: '已解析历史需求',
    loading: '正在加载历史需求...',
    empty: '暂无历史需求',
    source: '来源文档',
    sourceAll: '全部来源文档',
    selectedRequirementsCount: '已选需求 {count} 条',
    searchPlaceholder: '搜索',
    typeAll: '全部类型',
    priorityAll: '全部优先级'
  },
  result: {
    title: '分析摘要',
    requirementsCount: '需求数量',
    testPointsCount: '测试点数量',
    businessRulesCount: '业务规则数量',
    totalCount: '总计',
    selected: '已选文档',
    selectedDocumentsCount: '已选文档 {count} 个'
  },
  requirement: {
    id: '编号',
    title: '标题',
    content: '需求内容',
    type: '类型',
    priority: '优先级',
    category: '分类',
    statusLabel: '状态',
    editTitle: '编辑需求',
    editLoading: '正在加载需求详情…',
    editEmpty: '未选择需求',
    updateFailed: '保存需求失败',
    updateSuccess: '需求已保存'
  },
  message: {
    loadFailed: '加载文档列表失败',
    refreshSuccess: '文档列表已刷新',
    uploadSuccess: '文档上传成功',
    uploadFailed: '文档上传失败',
    analyzeSuccess: '文档分析成功',
    analyzeFailed: '文档分析失败',
    analyzeInProgress: '该文档正在分析，请等待当前分析结束',
    generateSuccess: '测试用例生成已触发',
    generateFailed: '生成测试用例失败',
    generatePartial: '已入库 {saved} 条用例，{failed} 条需求失败。已入库的用例已保留。',
    exportRequirementsSuccess: '需求导出已开始',
    exportRequirementsFailed: '导出需求失败',
    selectDocumentFirst: '请先选择一个文档',
    noAnalysisResult: '当前没有可用于生成用例的分析结果',
    searchFailed: '搜索失败',
    loadAnalysisFailed: '分析结果加载失败',
    previewFailed: '文档预览加载失败',
    noDocumentSelection: '请选择要删除的文档',
    noRequirementSelection: '请选择要删除的需求',
    resultNotReady: '当前文档暂无可展示的分析结果，请先执行分析',
    resultLoadedFromHistory: '已加载该文档的历史分析结果',
    deleteDocumentSuccess: '文档删除成功',
    deleteRequirementSuccess: '需求删除成功',
    deleteDocumentsPartial: '删除文档部分成功（成功 {success}，失败 {failed}）',
    deleteRequirementsPartial: '删除需求部分成功（成功 {success}，失败 {failed}）',
    previewCopySuccess: '预览内容已复制',
    previewCopyFailed: '复制预览内容失败'
  },
  confirm: {
    generateCases: '是否基于当前分析结果生成测试用例？',
    batchGenerateTitle: '批量生成确认',
    batchGenerateByRequirementsMessage: '批量生成：将处理需求 {reqCount} 条（每需求 {perReq} 条，约 {caseCount} 条用例）。继续？',
    batchGenerateByDocumentsMessage: '批量生成：文档 {count} 个，处理需求 {reqCount} 条（每需求 {perReq} 条，约 {caseCount} 条用例），跳过未分析 {skippedCount} 个。继续？',
    deleteDocuments: '确认删除选中文档吗？删除后无法恢复。',
    deleteRequirements: '确认删除选中需求吗？删除后无法恢复。'
  }
};
