export default {
  page: {
    title: 'Dashboard',
    subtitle: 'A unified overview of core business, system status, and entry points'
  },
  welcome: {
    kicker: 'Welcome back',
    title: 'TestPilot Overview',
    description: 'Unified view of key metrics across configuration, knowledge, documents, cases, and chat.'
  },
  actions: {
    refresh: 'Refresh overview',
    refreshing: 'Refreshing',
    export: 'Export stats',
    exporting: 'Exporting',
    bundleExport: 'Export Bundle',
    bundleExporting: 'Exporting Bundle'
  },
  kpi: {
    totalCases: 'Total cases',
    totalDocuments: 'Total documents',
    totalKnowledge: 'Knowledge files',
    totalChatSessions: 'Chat sessions',
    casesHint: 'From the Cases flow',
    documentsHint: 'From the Documents flow',
    knowledgeHint: 'From the Knowledge flow',
    chatHint: 'From the Chat flow',
    recentDocuments: 'Recent analyses',
    recentChats: 'Recent messages'
  },
  system: {
    title: 'System Status',
    subtitle: 'Health, services, and key runtime signals',
    overall: 'Overall',
    updatedAt: 'Updated at',
    healthTitle: 'Service health',
    healthHint: 'The health endpoint did not return extra details',
    aiService: 'AI service',
    knowledge: 'Knowledge service',
    performance: 'Performance',
    network: 'Network',
    networkLabel: 'Current access',
    networkHidden: 'Access address hidden for security',
    model: 'Model',
    responseTime: 'Response time',
    documents: 'Documents',
    vectors: 'Vectors',
    cpu: 'CPU',
    memory: 'Memory',
    disk: 'Disk',
    unknown: 'Unknown',
    modelStatus: {
      configError: 'Configuration error',
      serviceUnavailable: 'Service unavailable',
      connectionFailed: 'Connection failed',
      unknownModel: 'Unknown model'
    }
  },
  activities: {
    title: 'Recent Activities',
    subtitle: 'A compact feed of recent generations, analyses, and updates',
    emptyTitle: 'No recent activity',
    emptyMessage: 'There are no recent activity records to show yet.',
    types: {
      case: 'Case',
      requirement: 'Document analysis',
      knowledge: 'Knowledge base',
      chat: 'Chat',
      other: 'Other'
    },
    fallback: {
      case: '{count} case updates',
      requirement: '{count} document analyses',
      knowledge: '{count} knowledge file updates',
      chat: '{count} chat messages'
    }
  },
  shortcuts: {
    title: 'Shortcuts',
    subtitle: 'One-click navigation'
  },
  advanced: {
    title: 'Advanced Metrics',
    subtitle: 'Performance, usage, and token perspectives',
    perfCategoryCount: 'Performance categories',
    perfCategoryHint: 'Categories captured in last 24h',
    topUsageCategory: 'Top usage category',
    count: 'Count',
    totalTokens: 'Total tokens',
    avgTokens: 'Avg per message',
    topTokenModel: 'Top token model',
    tokens: 'Tokens',
    logsTotal: 'Total logs',
    logsError: 'Error logs'
  },
  state: {
    loadingOverview: 'Loading overview...',
    loadingSystem: 'Loading system status...',
    loadingActivities: 'Loading recent activities...',
    loadingHint: 'Local failures will not blank the page',
    emptyNetwork: 'No network info available'
  },
  message: {
    overviewFailed: 'Failed to load dashboard overview',
    healthFailed: 'Failed to load health status',
    systemFailed: 'Failed to load system status',
    activitiesFailed: 'Failed to load recent activities',
    networkFailed: 'Failed to load network info',
    logsFailed: 'Failed to load log statistics',
    partialFailure: 'Some data failed to load, so the page is showing a degraded view',
    exportSuccess: 'Statistics exported successfully',
    exportFailed: 'Failed to export statistics',
    bundleExportSuccess: 'Bundle exported successfully',
    bundleExportFailed: 'Failed to export bundle'
  }
};
