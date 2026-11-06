export default {
  page: {
    title: '总览'
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
    totalRequirements: '需求总数',
    recentNew: '近 {days} 天新增 {count}',
    recentMessages: '近 {days} 天消息 {count}',
    totalCases: '用例总数',
    totalKnowledge: '知识文件总数',
    totalChatSessions: '聊天会话数'
  },
  system: {
    title: '系统状态',
    updatedAt: '更新时间',
    aiService: 'AI 服务',
    aiServiceRowHint: '请在配置中心检查接口与模型设置',
    knowledge: '知识服务',
    performance: '系统性能',
    model: '模型',
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
    emptyTitle: '暂无最近活动',
    groupCountSummary: '近 {days} 天 {count} 条，最近：{latest}',
    viewAll: '查看全部 {count} 条',
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
    title: '快捷入口'
  },
  attention: {
    offlineTitle: '后端未连接',
    offlineMessage: '无法拉取实时指标，请确认服务已启动后刷新。',
    aiTitle: 'AI 服务需要关注',
    aiMessage: '当前模型或连接异常，生成与聊天可能不可用。',
    aiAction: '打开配置中心',
    reliabilityTitle: '系统可信度偏低'
  },
  advanced: {
    title: '高级指标',
    recentCases: '近 {days} 天新增用例',
    recentRequirements: '近 {days} 天新增需求',
    recentChats: '近 {days} 天聊天消息',
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
    loadingActivities: '正在加载最近活动...'
  },
  message: {
    overviewFailed: '总览数据加载失败',
    healthFailed: '健康状态加载失败',
    systemFailed: '系统状态加载失败',
    activitiesFailed: '最近活动加载失败',
    logsFailed: '运行日志统计加载失败',
    advancedFailed: '高级指标加载失败',
    partialFailure: '部分数据加载失败，页面已降级显示',
    exportSuccess: '统计导出成功',
    exportFailed: '统计导出失败',
    bundleExportSuccess: '打包导出成功',
    bundleExportFailed: '打包导出失败'
  }
};
