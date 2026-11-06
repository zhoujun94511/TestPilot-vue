/** 实验工具页复用的聊天会话 ID；登出时清掉，避免下一个账号接着用 */
export const EXPERIMENTAL_TOOLS_SESSION_STORAGE_KEY = 'testpilot_experimental_tools_session_id';

/** requirement：从当前账号可见的需求里下拉选择 */
export type ExperimentalToolFieldType = 'number' | 'text' | 'textarea' | 'boolean' | 'requirement';

export interface ExperimentalToolFieldDef {
  key: string;
  type: ExperimentalToolFieldType;
  required?: boolean;
  defaultValue?: string | number | boolean;
  min?: number;
  max?: number;
  /** 同名字段在不同工具里含义不同时，指定另一条占位文案 */
  placeholderKey?: string;
}

export interface ExperimentalToolDef {
  id: string;
  fields: ExperimentalToolFieldDef[];
  /** 至少填写其中一个字段 */
  requiredOneOf?: string[];
}

/**
 * 与 experiments/action_runtime/orchestrator 注册表对齐（显式 execute，不走 NL 猜工具）。
 * 增删工具时须同步改 orchestrator._register_builtin_tools，否则 API 返回 unknown_tool。
 */
export const EXPERIMENTAL_TOOL_DEFS: ExperimentalToolDef[] = [
  {
    id: 'rule_skeleton_cases',
    requiredOneOf: ['requirement_text', 'requirement_id'],
    fields: [
      { key: 'requirement_text', type: 'textarea' },
      { key: 'requirement_id', type: 'requirement' },
      { key: 'case_count', type: 'number', defaultValue: 5, min: 1, max: 10 },
      { key: 'use_llm', type: 'boolean', defaultValue: true }
    ]
  },
  {
    id: 'ac_coverage_review',
    fields: [
      { key: 'requirement_id', type: 'requirement', required: true, placeholderKey: 'requirement_id_required' }
    ]
  },
  {
    id: 'trace_matrix',
    fields: [{ key: 'limit', type: 'number', defaultValue: 50, min: 1, max: 200 }]
  }
];

export function getExperimentalToolDef(toolId: string): ExperimentalToolDef | undefined {
  return EXPERIMENTAL_TOOL_DEFS.find((item) => item.id === toolId);
}

/** 可从聊天输入框一键带入的字段（长文本/检索词） */
export const COMPOSER_CONTEXT_FIELD_KEYS = new Set(['requirement_text', 'content', 'query']);

export function toolComposerContextFieldKeys(toolId: string): string[] {
  const def = getExperimentalToolDef(toolId);
  if (!def) return [];
  return def.fields.map((f) => f.key).filter((key) => COMPOSER_CONTEXT_FIELD_KEYS.has(key));
}

/** 智能建议文案是否适合预填「生成用例」 */
export function looksLikeGenerateCasesSuggestion(text: string): boolean {
  const raw = String(text || '').trim();
  if (!raw) return false;
  const hasCase = /用例|case/i.test(raw);
  const hasGen = /设计|生成|编写|撰写|写|generate|design/i.test(raw);
  return hasCase && hasGen;
}

export function defaultFieldValuesForTool(toolId: string): Record<string, string | number | boolean> {
  const def = getExperimentalToolDef(toolId);
  if (!def) return {};
  const values: Record<string, string | number | boolean> = {};
  for (const field of def.fields) {
    if (field.defaultValue !== undefined) {
      values[field.key] = field.defaultValue;
    } else if (field.type === 'boolean') {
      values[field.key] = false;
    } else if (field.type === 'number') {
      values[field.key] = field.min ?? 1;
    } else {
      values[field.key] = '';
    }
  }
  return values;
}

export function buildExperimentalToolArgs(
  toolId: string,
  values: Record<string, string | number | boolean>
): Record<string, unknown> {
  const def = getExperimentalToolDef(toolId);
  if (!def) return {};
  const args: Record<string, unknown> = {};
  for (const field of def.fields) {
    const raw = values[field.key];
    if (field.type === 'number') {
      const num = Number(raw);
      if (!Number.isFinite(num)) continue;
      let clamped = num;
      if (field.min != null) clamped = Math.max(field.min, clamped);
      if (field.max != null) clamped = Math.min(field.max, clamped);
      args[field.key] = clamped;
      continue;
    }
    if (field.type === 'boolean') {
      args[field.key] = Boolean(raw);
      continue;
    }
    const text = String(raw ?? '').trim();
    if (!text && !field.required) continue;
    args[field.key] = text;
  }
  return args;
}

export function validateExperimentalToolForm(
  toolId: string,
  values: Record<string, string | number | boolean>
): string | null {
  const def = getExperimentalToolDef(toolId);
  if (!def) return 'unknown_tool';
  for (const field of def.fields) {
    if (!field.required) continue;
    const raw = values[field.key];
    if (field.type === 'boolean') continue;
    if (field.type === 'number') {
      if (!Number.isFinite(Number(raw))) return field.key;
      continue;
    }
    if (!String(raw ?? '').trim()) return field.key;
  }
  if (def.requiredOneOf?.length && !def.requiredOneOf.some((key) => String(values[key] ?? '').trim())) {
    return def.requiredOneOf[0];
  }
  return null;
}
