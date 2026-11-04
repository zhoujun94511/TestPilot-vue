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
    title: 'Business overview',
    subtitle: 'Core counts across cases, documents, knowledge, and chat',
    totalCases: 'Total cases',
    totalDocuments: 'Total documents',
    totalKnowledge: 'Knowledge files',
    totalChatSessions: 'Chat sessions',
    casesHint: 'Scope: {name}',
    documentsHint: 'Scope: {name}',
    knowledgeHint: 'Scope: {name}',
    chatHint: 'Scope: {name}',
    recentDocuments: 'Recent analyses',
    recentChats: 'Recent messages'
  },
  system: {
    title: 'System Status',
    subtitle: 'Service health and key runtime signals',
    overall: 'Overall',
    updatedAt: 'Updated at',
    healthTitle: 'Service health',
    healthHint: 'The health endpoint did not return extra details',
    aiService: 'AI service',
    aiServiceRowHint: 'Check API and model settings in Configuration',
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
    subtitle: 'A compact feed of recent generations, analyses, and updates',
    emptyTitle: 'No recent activity',
    emptyMessage: 'There are no recent activity records to show yet.',
    groupCollapsedHint: '{count} items — expand for details',
    groupExpandedHint: 'Click to collapse details',
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
    title: 'Shortcuts',
    subtitle: 'Common workflows in one click',
    generateDesc: 'Generate test cases from requirements',
    uploadDesc: 'Upload and analyze requirement documents',
    chatDesc: 'Talk to the AI assistant',
    configDesc: 'Models, RAG, and system settings'
  },
  attention: {
    offlineTitle: 'Backend disconnected',
    offlineMessage: 'Live metrics are unavailable. Start the service and refresh.',
    aiTitle: 'AI service needs attention',
    aiMessage: 'Model or connectivity issues may block generation and chat.',
    aiAction: 'Open configuration',
    reliabilityTitle: 'Low system trust score',
    reliabilityMessage: 'Multiple services or the knowledge base need setup before production use.'
  },
  pulse: {
    title: 'Readiness',
    subtitle: 'Model, knowledge coverage, and trust score'
  },
  advanced: {
    title: 'Advanced Metrics',
    subtitle: 'Recent output and AI usage (complements KPI totals above)',
    emptyCollapsed:
      'No stats yet. Output fills 30-day metrics; 7-day tokens cover all logged LLM usage.',
    recentCases: 'Cases added ({days}d)',
    recentCasesHint: 'Summed by case creation date',
    recentRequirements: 'Requirements added ({days}d)',
    recentRequirementsHint: 'Summed by requirement creation date',
    recentChats: 'Chat messages ({days}d)',
    recentChatsHint: 'Summed by message creation date',
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
    logsFailed: 'Failed to load log stats',
    advancedFailed: 'Failed to load advanced metrics',
    partialFailure: 'Some data failed to load, so the page is showing a degraded view',
    exportSuccess: 'Statistics exported successfully',
    exportFailed: 'Failed to export statistics',
    bundleExportSuccess: 'Bundle exported successfully',
    bundleExportFailed: 'Failed to export bundle'
  }
};
