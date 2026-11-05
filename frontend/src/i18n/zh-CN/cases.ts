export default {
  page: {
    title: '测试用例',
    subtitle: '迁移核心用例闭环，验证列表、筛选、生成、批量操作、导出与统计能力'
  },
  tabs: {
    generate: '用例生成',
    manage: '用例管理'
  },
  generateMode: {
    aria: '生成方式'
  },
  toolbar: {
    manageLead: '查看统计与列表；导出与模板下载在「更多」中。',
    exportMenu: '导出与模板'
  },
  actions: {
    generate: '生成用例',
    batchGenerate: '批量生成',
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
    title: '单次生成'
  },
  batch: {
    title: '批量生成',
    requirementsPlaceholder: '登录校验;订单退款',
    requirementsHelper: '若存在多条需求，每条需求以 ; 做拆分！',
    processModeLabel: '处理模式',
    processModeHelper: '顺序：逐条；并行：多条同时'
  },
  state: {
    generatingTitle: '正在生成用例',
    generatingHint: '模型正在分析需求并写入用例，通常需要数十秒到数分钟，请勿关闭页面。',
    batchGeneratingTitle: '正在批量生成',
    batchGeneratingHint: '正在按需求逐条或并行生成，耗时与条数、是否启用知识库有关。'
  },
  form: {
    requirementLabel: '需求描述',
    requirementPlaceholder: '如：用户登录需校验账号状态与错误提示',
    requirementHelper: '写清功能或验收点即可；优先级由模型判断',
    caseCountLabel: '生成数量',
    caseCountOption: '{count} 个'
  },
  filters: {
    title: '搜索与筛选',
    keywordLabel: '关键词',
    keywordPlaceholder: '搜索',
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
    title: '用例列表',
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
      edit: '编辑',
      regenerate: '再生成',
      exportOne: '导出',
      deleteOne: '删除'
    }
  },
  edit: {
    title: '编辑用例',
    loading: '正在加载用例详情…',
    noCase: '未选择用例',
    descriptionLabel: '描述',
    preconditionLabel: '前置条件',
    stepsLabel: '测试步骤',
    expectedLabel: '预期结果',
    linesHelper: '每行一条',
    tagsHelper: '多个标签可用逗号分隔',
    tagsPlaceholder: '如：首页, 双端',
    stepsRequired: '请至少填写一条步骤与一条预期结果'
  },
  stats: {
    title: '统计信息',
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
    updateSuccess: '用例已保存',
    updateFailed: '保存用例失败',
    statsFailed: '加载统计信息失败',
    configFailed: '加载用例配置失败',
    requirementRequired: '请输入需求描述后再生成',
    requirementsRequired: '请输入至少一条需求后再批量生成'
  }
};
