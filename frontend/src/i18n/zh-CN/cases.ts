export default {
  page: {
    title: '测试用例',
    subtitle: '迁移核心用例闭环，验证列表、筛选、生成、批量操作、导出与统计能力'
  },
  tabs: {
    generate: '用例生成',
    manage: '用例管理'
  },
  actions: {
    generate: '生成用例',
    hideGenerate: '收起生成',
    batchGenerate: '批量生成',
    hideBatchGenerate: '收起批量生成',
    export: '导出',
    exporting: '导出中',
    exportExcel: 'Excel',
    exportCsv: 'CSV',
    exportJson: 'JSON',
    downloadTemplate: '下载模板',
    templateDownloading: '下载模板中',
    refresh: '刷新',
    generating: '生成中',
    batchGenerating: '批量生成中',
    deleteSelected: '删除已选',
    clearInput: '清空'
  },
  single: {
    title: '单次生成',
    hint: '输入一段需求描述即可生成测试用例',
    autoPriorityHint: '优先级由模型自动判断'
  },
  batch: {
    title: '批量生成',
    hint: '按行输入多个需求，每行生成一组测试用例',
    requirementsLabel: '需求列表',
    requirementsPlaceholder: '请输入多个需求，每行一个需求',
    processModeLabel: '处理模式',
    processHint: '当前接口支持顺序或并行处理'
  },
  form: {
    requirementLabel: '需求描述',
    requirementPlaceholder: '请输入需求描述、业务规则或测试目标',
    caseCountLabel: '生成数量',
    caseCountOption: '{count} 个',
    categoryLabel: '用例类别',
    categoryAll: '全部类别',
    useRag: '使用知识库增强',
    useRagDisabled: '当前知识库增强不可用，将使用纯模型生成'
  },
  filters: {
    title: '搜索与筛选',
    keywordLabel: '关键词',
    keywordPlaceholder: '输入标题、描述或用例编号',
    priorityLabel: '优先级',
    priorityAll: '全部优先级',
    statusLabel: '状态',
    statusAll: '全部状态',
    categoryLabel: '类别',
    categoryAll: '全部类别',
    apply: '查询',
    selectedCount: '已选择 {count} 条'
  },
  table: {
    empty: '暂无测试用例',
    loading: '正在加载测试用例...',
    noSteps: '暂无步骤',
    stepsPreview: '{count} 个步骤，首步：{sample}',
    columns: {
      caseId: '用例编号',
      title: '标题',
      priority: '优先级',
      status: '状态',
      category: '类别',
      testMethod: '测试方法',
      module: '功能模块',
      tags: '标签',
      steps: '步骤预览',
      updatedAt: '更新时间',
      actions: '操作'
    },
    actions: {
      regenerate: '再生成',
      exportOne: '导出',
      deleteOne: '删除'
    }
  },
  stats: {
    loading: '正在加载统计信息...',
    empty: '暂无统计信息',
    emptyHint: '当前没有可展示的统计结果',
    total: '总用例数',
    draft: '草稿',
    active: '生效',
    deprecated: '已废弃',
    totalHint: '来源于用例列表',
    statusHint: '按状态汇总',
    priorityDistribution: '优先级分布',
    categoryDistribution: '类别分布',
    emptyDistribution: '暂无分布数据'
  },
  confirm: {
    generateTitle: '确认生成测试用例',
    generateMessage: '将根据当前需求生成 {count} 条测试用例，是否继续？',
    batchGenerateTitle: '确认批量生成',
    batchGenerateMessage: '将对 {count} 条需求执行 {mode} 处理，是否继续？',
    regenerateTitle: '确认重新生成',
    regenerateMessage: '将基于「{title}」重新生成测试用例，是否继续？',
    deleteTitle: '确认删除测试用例',
    deleteMessage: '将删除「{title}」，该操作不可恢复，是否继续？',
    deleteBatchTitle: '确认批量删除测试用例',
    deleteBatchMessage: '将删除已选的 {count} 条测试用例，该操作不可恢复，是否继续？'
  },
  message: {
    loadFailed: '加载测试用例列表失败',
    refreshSuccess: '用例数据已刷新',
    generateSuccess: '已生成 {count} 条测试用例',
    generateFailed: '生成测试用例失败',
    batchGenerateSuccess: '批量生成完成，共生成 {count} 条测试用例',
    batchGenerateFailed: '批量生成测试用例失败',
    generateSynced: '已同步到用例管理，可继续筛选与导出',
    batchGenerateSynced: '批量结果已同步到用例管理，可继续筛选与导出',
    exportSuccess: '导出已开始',
    exportFailed: '导出测试用例失败',
    templateDownloadSuccess: '模板下载已开始',
    templateDownloadFailed: '下载模板失败',
    deleteSuccess: '测试用例已删除',
    deleteFailed: '删除测试用例失败',
    deleteBatchSuccess: '已删除 {count} 条测试用例',
    deleteBatchPartial: '部分删除成功：成功 {success} 条，失败 {failed} 条',
    deleteBatchFailed: '批量删除测试用例失败',
    statsFailed: '加载统计信息失败',
    configFailed: '加载用例配置失败',
    requirementRequired: '请输入需求描述后再生成',
    requirementsRequired: '请输入至少一条需求后再批量生成'
  },
  pagination: {
    pageInfo: '第 {page} / {pages} 页，共 {total} 条'
  }
};
