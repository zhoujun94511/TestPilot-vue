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
    title: '业务概览',
    subtitle: '用例、文档、知识与会话的核心数量',
    totalCases: '用例总数',
    totalDocuments: '文档总数',
    totalKnowledge: '知识文件总数',
    totalChatSessions: '聊天会话数',
    casesHint: '统计范围：{name}',
    documentsHint: '统计范围：{name}',
    knowledgeHint: '统计范围：{name}',
    chatHint: '统计范围：{name}',
    recentDocuments: '最近分析',
    recentChats: '最近消息'
  },
  system: {
    title: '系统状态',
    subtitle: '各服务健康与关键运行指标',
    overall: '整体状态',
    updatedAt: '更新时间',
    healthTitle: '服务健康',
    healthHint: '当前健康接口未返回补充信息',
    aiService: 'AI 服务',
    aiServiceRowHint: '请在配置中心检查接口与模型设置',
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
    runtimeLogs: '近 {hours}h 错误',
    runtimeLogsHint: '共 {total} 条日志 · 错误 {errors}',
    runtimeLogsNoEntries: '近 {hours}h 暂无系统日志',
    runtimeLogsEmpty: '日志统计暂不可用',
    unknown: '未知',
    limited: '仅超管可见',
    limitedHint: '主机 CPU、内存、磁盘指标仅超级管理员可查看',
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
    groupCollapsedHint: '共 {count} 条，点击展开查看详情',
    groupExpandedHint: '点击收起详情',
    types: {
      case: '用例',
      requirement: '文档分析',
      knowledge: '知识库',
      chat: '聊天',
      other: '其他'
    },
    messages: {
      case: '生成了测试用例：{subject}',
      requirement: '分析了需求文档：{subject}',
      knowledge: '上传了知识库文件：{subject}',
      chat: 'AI 助手会话：{subject}',
      other: '{subject}'
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
    subtitle: '常用工作流，一点即达',
    generateDesc: '从需求生成测试用例',
    uploadDesc: '上传并分析需求文档',
    chatDesc: '与 AI 助手对话',
    configDesc: '模型、知识库检索与系统参数'
  },
  attention: {
    offlineTitle: '后端未连接',
    offlineMessage: '无法拉取实时指标，请确认服务已启动后刷新。',
    aiTitle: 'AI 服务需要关注',
    aiMessage: '当前模型或连接异常，生成与聊天可能不可用。',
    aiAction: '打开配置中心',
    reliabilityTitle: '系统可信度偏低',
    reliabilityMessage: '多项服务状态或知识库为空，建议先完善配置与知识上传。'
  },
  pulse: {
    title: '就绪情况',
    subtitle: '模型、知识覆盖与系统可信度'
  },
  advanced: {
    title: '高级指标',
    subtitle: '近阶段业务产出与 AI 消耗（与上方 KPI 总量互补）',
    emptyCollapsed:
      '暂无统计数据；生成用例、分析需求或使用 AI 聊天后，此处会显示近 30 天产出与近 7 天全站 Token。',
    recentCases: '近 {days} 天新增用例',
    recentCasesHint: '按用例创建日汇总，反映用例生成活跃度',
    recentRequirements: '近 {days} 天新增需求',
    recentRequirementsHint: '按需求创建日汇总，反映文档分析产出',
    recentChats: '近 {days} 天聊天消息',
    recentChatsHint: '按聊天消息创建日汇总',
    totalTokensPeriod: '近 {days} 天 Token 消耗',
    badgeNoData: '暂无数据',
    tokensEmptyHint: '近 7 天暂无 LLM Token 记录',
    tokensHintCalls: '{n} 次调用',
    tokensHintAvg: '均 {n}/次'
  },
  state: {
    loadingOverview: '正在加载总览...',
    loadingSystem: '正在加载系统状态...',
    loadingAdvanced: '正在加载高级指标...',
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
    logsFailed: '运行日志统计加载失败',
    advancedFailed: '高级指标加载失败',
    partialFailure: '部分数据加载失败，页面已降级显示',
    exportSuccess: '统计导出成功',
    exportFailed: '统计导出失败',
    bundleExportSuccess: '打包导出成功',
    bundleExportFailed: '打包导出失败'
  }
};
