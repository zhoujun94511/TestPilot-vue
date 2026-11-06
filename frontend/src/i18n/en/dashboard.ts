export default {
  page: {
    title: 'Dashboard'
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
    title: 'Business overview',
    totalRequirements: 'Total requirements',
    recentNew: '{count} added in {days}d',
    recentMessages: '{count} messages in {days}d',
    totalCases: 'Total cases',
    totalKnowledge: 'Knowledge files',
    totalChatSessions: 'Chat sessions'
  },
  system: {
    title: 'System Status',
    updatedAt: 'Updated at',
    aiService: 'AI service',
    aiServiceRowHint: 'Check API and model settings in Configuration',
    knowledge: 'Knowledge service',
    performance: 'Performance',
    model: 'Model',
    documents: 'Documents',
    vectors: 'Vectors',
    cpu: 'CPU',
    memory: 'Memory',
    disk: 'Disk',
    runtimeLogs: 'Errors ({hours}h)',
    runtimeLogsHint: '{total} log entries · {errors} errors',
    runtimeLogsNoEntries: 'No system logs in the last {hours}h',
    runtimeLogsEmpty: 'Log stats unavailable',
    unknown: 'Unknown',
    limited: 'Super admin only',
    limitedHint: 'Host CPU, memory and disk metrics are visible to super admins only',
    modelStatus: {
      configError: 'Configuration error',
      serviceUnavailable: 'Service unavailable',
      connectionFailed: 'Connection failed',
      unknownModel: 'Unknown model'
    }
  },
  activities: {
    title: 'Recent Activities',
    emptyTitle: 'No recent activity',
    groupCountSummary: '{count} in {days} days. Latest: {latest}',
    viewAll: 'View all {count}',
    types: {
      case: 'Case',
      requirement: 'Document analysis',
      knowledge: 'Knowledge base',
      chat: 'AI Chat',
      other: 'Other'
    },
    messages: {
      case: 'Generated test case: {subject}',
      requirement: 'Analyzed requirement document: {subject}',
      knowledge: 'Uploaded knowledge file: {subject}',
      chat: 'AI chat session: {subject}',
      other: '{subject}'
    },
    fallback: {
      case: '{count} case updates',
      requirement: '{count} document analyses',
      knowledge: '{count} knowledge file updates',
      chat: '{count} chat messages'
    }
  },
  shortcuts: {
    title: 'Shortcuts'
  },
  attention: {
    offlineTitle: 'Backend disconnected',
    offlineMessage: 'Live metrics are unavailable. Start the service and refresh.',
    aiTitle: 'AI service needs attention',
    aiMessage: 'Model or connectivity issues may block generation and chat.',
    aiAction: 'Open configuration',
    reliabilityTitle: 'Low system trust score'
  },
  advanced: {
    title: 'Advanced Metrics',
    recentCases: 'Cases added ({days}d)',
    recentRequirements: 'Requirements added ({days}d)',
    recentChats: 'Chat messages ({days}d)',
    totalTokensPeriod: 'Token usage ({days}d)',
    badgeNoData: 'No data',
    tokensEmptyHint: 'No token usage in the last 7 days',
    tokensHintCalls: '{n} calls',
    tokensHintAvg: 'avg {n}/call'
  },
  state: {
    loadingOverview: 'Loading overview...',
    loadingSystem: 'Loading system status...',
    loadingAdvanced: 'Loading advanced metrics...',
    loadingActivities: 'Loading recent activities...'
  },
  message: {
    overviewFailed: 'Failed to load dashboard overview',
    healthFailed: 'Failed to load health status',
    systemFailed: 'Failed to load system status',
    activitiesFailed: 'Failed to load recent activities',
    logsFailed: 'Failed to load log stats',
    advancedFailed: 'Failed to load advanced metrics',
    partialFailure: 'Some data failed to load, so the page is showing a degraded view',
    exportSuccess: 'Statistics exported successfully',
    exportFailed: 'Failed to export statistics',
    bundleExportSuccess: 'Bundle exported successfully',
    bundleExportFailed: 'Failed to export bundle'
  }
};
