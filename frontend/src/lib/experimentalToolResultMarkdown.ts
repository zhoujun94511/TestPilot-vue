import type { ComposerTranslation } from 'vue-i18n';
import { asRecord, toDisplayValue } from '@/composables/chat/chatDisplayUtils';

function parseMaybeJsonArray(value: unknown): unknown[] | null {
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string') return null;
  const text = value.trim();
  if (!text.startsWith('[') || !text.endsWith(']')) return null;
  try {
    const parsed = JSON.parse(text);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function formatTextList(value: unknown, maxItems = 6): string {
  if (typeof value === 'string' && !value.trim().startsWith('[')) {
    return value.trim() || '-';
  }
  const list = parseMaybeJsonArray(value) || [];
  if (!list.length) return '-';
  return list
    .slice(0, maxItems)
    .map((item, index) => `${index + 1}. ${String(toDisplayValue(item) || '').trim() || '-'}`)
    .join('\n');
}

function records(value: unknown): Record<string, unknown>[] {
  return (Array.isArray(value) ? value : [])
    .map((raw) => asRecord(raw))
    .filter((item): item is Record<string, unknown> => Boolean(item));
}

function cell(value: unknown): string {
  return String(toDisplayValue(value)).replace(/\|/g, '\\|').replace(/\s*\n\s*/g, ' ');
}

function formatJsonPreview(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function isGenericSuccessMessage(t: ComposerTranslation, text: string): boolean {
  const normalized = String(text || '').trim().toLowerCase();
  if (normalized === 'message sent successfully' || normalized === 'success' || normalized === 'ok') {
    return true;
  }
  return (
    normalized === t('chat.toolMarkdown.genericActionSuccess').toLowerCase()
    || normalized === t('chat.toolMarkdown.genericOperationSuccess').toLowerCase()
  );
}

function formatCaseBlock(t: ComposerTranslation, item: Record<string, unknown>): string[] {
  const lines = [`#### ${toDisplayValue(item.title)}`];
  const covers = String(item.covers || '').trim();
  if (covers) lines.push(`- ${t('chat.toolMarkdown.covers')}: ${covers}`);
  lines.push(`- ${t('chat.toolMarkdown.priority')}: ${toDisplayValue(item.priority)}`);
  lines.push(`- ${t('chat.toolMarkdown.steps')}:\n${formatTextList(item.steps)}`);
  lines.push(`- ${t('chat.toolMarkdown.expectedResult')}:\n${formatTextList(item.expected_result)}`);
  lines.push('');
  return lines;
}

function scenarioLabels(t: ComposerTranslation, value: unknown): string {
  const keys = Array.isArray(value) ? value.map(String) : [];
  if (!keys.length) return t('chat.toolMarkdown.none');
  return keys
    .map((key) => {
      const path = `chat.toolMarkdown.scenario.${key}`;
      const label = t(path);
      return label === path ? key : label;
    })
    .join('、');
}

function formatSkeletonPreview(t: ComposerTranslation, output: Record<string, unknown>): string[] {
  const cases = records(output.cases);
  const ruleCases = cases.filter((item) => item.source === 'rule');
  const llmCases = cases.filter((item) => item.source !== 'rule');
  const lines = [`**${t('chat.toolMarkdown.scenarios')}**: ${scenarioLabels(t, output.scenarios)}`];
  const note = String(output.llm_note || '').trim();
  if (note) lines.push(`> ${note}`);
  lines.push('');
  lines.push(`### ${t('chat.toolMarkdown.ruleCases', { count: ruleCases.length })}`);
  if (!ruleCases.length) lines.push(t('chat.toolMarkdown.none'));
  ruleCases.forEach((item) => lines.push(...formatCaseBlock(t, item)));
  lines.push(`### ${t('chat.toolMarkdown.llmCases', { count: llmCases.length })}`);
  if (!llmCases.length) lines.push(t('chat.toolMarkdown.none'));
  llmCases.forEach((item) => lines.push(...formatCaseBlock(t, item)));
  return lines;
}

const STRUCTURE_ISSUE_CODES = [
  'title_too_short',
  'steps_missing',
  'steps_too_few',
  'steps_vague',
  'expected_missing'
];

function formatCoverage(t: ComposerTranslation, output: Record<string, unknown>): string[] {
  const requirement = asRecord(output.requirement) || {};
  const criteria = records(output.criteria);
  const lines = [
    `**${t('chat.toolMarkdown.requirement')}**: \`${toDisplayValue(requirement.req_id)}\` ${toDisplayValue(requirement.title)}`,
    `**${t('chat.toolMarkdown.linkedCases')}**: ${toDisplayValue(output.case_count)}`,
    ''
  ];
  if (!criteria.length) {
    lines.push(t('chat.toolMarkdown.noCriteria'));
  } else {
    lines.push(
      `| ${t('chat.toolMarkdown.criterion')} | ${t('chat.toolMarkdown.coverageState')} | ${t('chat.toolMarkdown.matchedCase')} | ${t('chat.toolMarkdown.score')} |`
    );
    lines.push('| --- | --- | --- | --- |');
    for (const row of criteria) {
      const state = row.covered ? t('chat.toolMarkdown.covered') : t('chat.toolMarkdown.gap');
      const matched = row.covered ? `${cell(row.case_title)}（${cell(row.case_id)}）` : '-';
      lines.push(`| ${cell(row.criterion)} | ${state} | ${matched} | ${cell(row.score)} |`);
    }
  }
  const issues = records(output.structure_issues);
  lines.push('');
  lines.push(`### ${t('chat.toolMarkdown.structureIssues', { count: issues.length })}`);
  if (!issues.length) lines.push(t('chat.toolMarkdown.none'));
  for (const item of issues) {
    const codes = Array.isArray(item.issues) ? item.issues.map(String) : [];
    const labels = codes
      .map((code) => (STRUCTURE_ISSUE_CODES.includes(code) ? t(`chat.toolMarkdown.issue.${code}`) : code))
      .join('、');
    lines.push(`- \`${toDisplayValue(item.case_id)}\` ${toDisplayValue(item.title)}：${labels}`);
  }
  return lines;
}

function traceSection(
  t: ComposerTranslation,
  key: string,
  total: unknown,
  items: Record<string, unknown>[],
  render: (item: Record<string, unknown>) => string
): string[] {
  const lines = [`### ${t(`chat.toolMarkdown.trace.${key}`, { count: toDisplayValue(total) })}`];
  if (!items.length) {
    lines.push(t('chat.toolMarkdown.none'));
  } else {
    items.forEach((item) => lines.push(`- ${render(item)}`));
    if (Number(total) > items.length) {
      lines.push(`> ${t('chat.toolMarkdown.listTruncated', { shown: items.length, total: toDisplayValue(total) })}`);
    }
  }
  lines.push('');
  return lines;
}

function formatTrace(t: ComposerTranslation, output: Record<string, unknown>): string[] {
  const counts = asRecord(output.counts) || {};
  const reqLine = (item: Record<string, unknown>) => `\`${toDisplayValue(item.req_id)}\` ${toDisplayValue(item.title)}`;
  const caseLine = (item: Record<string, unknown>) => `\`${toDisplayValue(item.case_id)}\` ${toDisplayValue(item.title)}`;
  return [
    ...traceSection(t, 'requirementsWithoutCases', counts.requirements_without_cases,
      records(output.requirements_without_cases), reqLine),
    ...traceSection(t, 'casesWithMissingRequirement', counts.cases_with_missing_requirement,
      records(output.cases_with_missing_requirement),
      (item) => `${caseLine(item)} → \`${toDisplayValue(item.requirement_id)}\``),
    ...traceSection(t, 'casesUnlinked', counts.cases_unlinked, records(output.cases_unlinked), caseLine),
    ...traceSection(t, 'requirementsWithCases', counts.requirements_with_cases,
      records(output.requirements_with_cases),
      (item) => `${reqLine(item)}：${t('chat.toolMarkdown.trace.caseCount', { count: toDisplayValue(item.case_count) })}`)
  ];
}

/** 已入库的用例走表格，并带「去用例管理高亮」链接 */
export function extractExperimentalToolTable(
  toolName: string,
  toolResults: Record<string, unknown> | null
): { kind: 'cases'; rows: Record<string, unknown>[] } | null {
  if (!toolResults || toolName !== 'rule_skeleton_cases' || toolResults.dry_run !== false) return null;
  const rows = records(toolResults.cases).map((item) => ({
    case_id: toDisplayValue(item.case_id),
    title: toDisplayValue(item.title),
    priority: toDisplayValue(item.priority),
    status: toDisplayValue(item.status),
    module: toDisplayValue(item.module)
  }));
  return rows.length ? { kind: 'cases', rows } : null;
}

export function formatActionResultContent(
  t: ComposerTranslation,
  messageText: string,
  toolName: string,
  toolResults: Record<string, unknown> | null
): string {
  const cleanMessage = isGenericSuccessMessage(t, messageText) ? '' : String(messageText || '').trim();
  if (!toolResults) return cleanMessage || t('chat.state.emptyMessage');
  const toolMessage = String(toolResults.message || '').trim();
  const parts: string[] = [];
  if (toolMessage) parts.push(`**${toolMessage}**`, '');
  else if (cleanMessage) parts.push(cleanMessage, '');
  if (toolResults.success === false) {
    return parts.join('\n').trim() || cleanMessage || t('chat.state.emptyMessage');
  }
  if (toolName === 'rule_skeleton_cases') {
    parts.push(...formatSkeletonPreview(t, toolResults));
  } else if (toolName === 'ac_coverage_review') {
    parts.push(...formatCoverage(t, toolResults));
  } else if (toolName === 'trace_matrix') {
    parts.push(...formatTrace(t, toolResults));
  } else {
    parts.push('```json', formatJsonPreview(toolResults), '```');
  }
  return parts.join('\n').trim() || t('chat.state.emptyMessage');
}
