export default {
  page: {
    title: '总览',
    subtitle: '汇总当前 TestPilot 的核心业务、系统状态与入口'
  },
  welcome: {
    kicker: '欢迎回来',
    title: 'TestPilot 总览',
    description: '统一展示配置、知识、文档、用例与会话关键指标。'
  },
  actions: {
    refresh: '刷新总览',
    refreshing: '刷新中',
    export: '导出统计',
    exporting: '导出中',
    bundleExport: '打包导出',
    bundleExporting: '打包导出中'
  },
  kpi: {
    totalCases: '用例总数',
    totalDocuments: '文档总数',
    totalKnowledge: '知识文件总数',
    totalChatSessions: '聊天会话数',
    casesHint: '来自 Cases 闭环',
    documentsHint: '来自 Documents 闭环',
    knowledgeHint: '来自 Knowledge 闭环',
    chatHint: '来自 Chat 闭环',
    recentDocuments: '最近分析',
    recentChats: '最近消息'
  },
  system: {
    title: '系统状态',
    subtitle: '健康、服务和关键运行指标',
    overall: '整体状态',
    updatedAt: '更新时间',
    healthTitle: '服务健康',
    healthHint: '当前健康接口未返回补充信息',
    aiService: 'AI 服务',
    knowledge: '知识服务',
    performance: '系统性能',
    network: '网络信息',
    networkLabel: '当前访问',
    networkHidden: '出于安全考虑，已隐藏访问地址',
    model: '模型',
    responseTime: '响应时间',
    documents: '文档数',
    vectors: '向量数',
    cpu: 'CPU',
    memory: '内存',
    disk: '磁盘',
    unknown: '未知',
    modelStatus: {
      configError: '配置错误',
      serviceUnavailable: '服务不可用',
      connectionFailed: '连接失败',
      unknownModel: '未知模型'
    }
  },
  activities: {
    title: '最近活动',
    subtitle: '最近生成、分析与更新的汇总',
    emptyTitle: '暂无最近活动',
    emptyMessage: '当前没有可展示的最近活动记录。',
    types: {
      case: '用例',
      requirement: '文档分析',
      knowledge: '知识库',
      chat: '聊天',
      other: '其他'
    },
    fallback: {
      case: '{count} 条用例更新',
      requirement: '{count} 条文档分析',
      knowledge: '{count} 个知识文件更新',
      chat: '{count} 条聊天消息'
    }
  },
  shortcuts: {
    title: '快捷入口',
    subtitle: '一键跳转'
  },
  advanced: {
    title: '高级指标',
    subtitle: '性能、使用与 Token 视角',
    perfCategoryCount: '性能指标分类数',
    perfCategoryHint: '近 24 小时采集到的分类',
    topUsageCategory: '最高使用分类',
    count: '次数',
    totalTokens: 'Token 总量',
    avgTokens: '平均每条消息',
    topTokenModel: 'Token 最高模型',
    tokens: 'Token',
    logsTotal: '日志总量',
    logsError: '错误日志'
  },
  state: {
    loadingOverview: '正在加载总览...',
    loadingSystem: '正在加载系统状态...',
    loadingActivities: '正在加载最近活动...',
    loadingHint: '局部失败不会影响整页展示',
    emptyNetwork: '暂无网络信息'
  },
  message: {
    overviewFailed: '总览数据加载失败',
    healthFailed: '健康状态加载失败',
    systemFailed: '系统状态加载失败',
    activitiesFailed: '最近活动加载失败',
    networkFailed: '网络信息加载失败',
    logsFailed: '日志统计加载失败',
    partialFailure: '部分数据加载失败，页面已降级显示',
    exportSuccess: '统计导出成功',
    exportFailed: '统计导出失败',
    bundleExportSuccess: '打包导出成功',
    bundleExportFailed: '打包导出失败'
  }
};
