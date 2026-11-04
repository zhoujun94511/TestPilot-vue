import { get, post } from '@/api/http';
import {
  normalizeError as coreNormalizeError,
  normalizeResponse as coreNormalizeResponse,
  pickCompatField,
  isRecord
} from '@/api/core';

export interface ExperimentalActionPlan {
  intent?: string | null;
  tool_name?: string | null;
  args?: Record<string, unknown> | null;
  risk_level?: string | null;
  requires_confirmation?: boolean | null;
  reason?: string | null;
}

export interface ExperimentalExecutePayload {
  query: string;
  session_id?: string;
  user_id?: string;
  require_confirmation?: boolean;
  tool_name: string;
  args?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface ExperimentalExecuteResult {
  success: boolean;
  execution_id?: string;
  status?: string;
  message?: string;
  plan?: ExperimentalActionPlan | null;
  tool_output?: Record<string, unknown> | null;
  error?: string;
  raw?: Record<string, unknown>;
}

export interface ExperimentalToolsHealth {
  success: boolean;
  tools: Record<string, string>;
  allow_nl?: boolean;
  explicit_only?: boolean;
}

function normalizeExecuteResult(payload: Record<string, unknown>): ExperimentalExecuteResult {
  const planRaw = pickCompatField(payload, ['plan'], null);
  const plan = isRecord(planRaw) ? (planRaw as ExperimentalActionPlan) : null;
  const toolOutput = pickCompatField(payload, ['tool_output'], null);
  return {
    success: Boolean(pickCompatField(payload, ['success'], false)),
    execution_id: pickCompatField(payload, ['execution_id'], undefined),
    status: String(pickCompatField(payload, ['status'], '') || ''),
    message: String(pickCompatField(payload, ['message'], '') || ''),
    plan,
    tool_output: isRecord(toolOutput) ? toolOutput : null,
    error: pickCompatField(payload, ['error'], undefined),
    raw: payload
  };
}

export async function fetchExperimentalActionsHealth(): Promise<ExperimentalToolsHealth> {
  try {
    const response = await get<unknown>('/experimental-actions/health');
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to load experimental actions health'
    });
    const toolsRaw = pickCompatField(payload, ['tools'], {});
    const tools: Record<string, string> = {};
    if (isRecord(toolsRaw)) {
      for (const [name, risk] of Object.entries(toolsRaw)) {
        tools[String(name)] = String(risk || 'low');
      }
    }
    return {
      success: Boolean(pickCompatField(payload, ['success'], true)),
      tools,
      allow_nl: Boolean(pickCompatField(payload, ['allow_nl'], false)),
      explicit_only: Boolean(pickCompatField(payload, ['explicit_only'], true))
    };
  } catch (error) {
    coreNormalizeError(error, 'Failed to load experimental actions health');
  }
}

export async function executeExperimentalAction(body: ExperimentalExecutePayload): Promise<ExperimentalExecuteResult> {
  try {
    const response = await post<unknown>('/experimental-actions/execute', {
      query: body.query,
      session_id: body.session_id,
      user_id: body.user_id,
      require_confirmation: body.require_confirmation ?? true,
      tool_name: body.tool_name,
      args: body.args ?? {},
      metadata: body.metadata ?? {}
    });
    const payload = coreNormalizeResponse<Record<string, unknown>>(response, {
      fallbackMessage: 'Failed to execute experimental action'
    });
    return normalizeExecuteResult(payload);
  } catch (error) {
    coreNormalizeError(error, 'Failed to execute experimental action');
  }
}
