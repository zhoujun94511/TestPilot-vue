#!/usr/bin/python
# -*- coding: utf-8 -*-
import inspect
import json
import uuid
from typing import Callable, Dict, Any

from config.settings import settings as app_settings
from models.models import db, ToolExecutionLog
from utils.utils_core.logger import get_logger

from .registry import ToolRegistry
from .schemas import ActionPlan, ActionRequest, ActionResult
from .toolkit import (
    tool_ac_coverage_review,
    tool_rule_skeleton_cases,
    tool_trace_matrix,
)

logger = get_logger(__name__)

# 预览后才能入库的工具：确认时按预览原样保存，不重新调用模型。
PREVIEW_THEN_SAVE_TOOLS = {"rule_skeleton_cases"}
_PREVIEW_ONLY_ARGS = ("save", "preview_cases")


def _accepted_args(handler: Callable, args: Dict[str, Any]) -> Dict[str, Any]:
    params = inspect.signature(handler).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(args)
    return {k: v for k, v in args.items() if k in params}


class ExperimentalActionOrchestrator:
    """Experimental tool orchestrator.

    This module is designed to be optional and detachable:
    - Lives under experiments/ namespace
    - Works with explicit feature flag
    - Writes only after the user confirms a preview
    """

    def __init__(self):
        self.registry = ToolRegistry()
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.registry.register("rule_skeleton_cases", tool_rule_skeleton_cases, risk_level="medium")
        self.registry.register("ac_coverage_review", tool_ac_coverage_review, risk_level="low")
        self.registry.register("trace_matrix", tool_trace_matrix, risk_level="low")

    _CASUAL_EXACT = {
        "你好", "您好", "hi", "hello", "hey", "在吗", "在不在", "谢谢", "感谢",
        "thanks", "thank you", "再见", "bye", "ok", "okay", "嗯", "好的", "行",
    }

    _TRACE_HINTS = ("追溯", "trace", "traceability", "没有用例的需求", "未关联")

    @classmethod
    def _has_tool_intent(cls, raw_text: str) -> bool:
        text = (raw_text or "").strip()
        if not text:
            return False
        lowered = text.lower()
        if lowered in cls._CASUAL_EXACT or text in cls._CASUAL_EXACT:
            return False
        return any(h in lowered or h in text for h in cls._TRACE_HINTS)

    @staticmethod
    def _no_tool_plan(reason: str) -> ActionPlan:
        return ActionPlan(
            intent="none",
            tool_name="",
            args={},
            risk_level="low",
            reason=reason,
            requires_confirmation=False,
        )

    def _plan_from_explicit_metadata(self, request: ActionRequest) -> ActionPlan | None:
        metadata = request.metadata or {}
        tool_name = str(metadata.get("tool_name") or "").strip()
        if not tool_name:
            return None
        if not self.registry.get(tool_name):
            return None
        args = metadata.get("args") if isinstance(metadata.get("args"), dict) else {}
        merged_args = dict(args)
        for key in ("limit", "requirement_text", "requirement_id", "case_count", "use_llm"):
            if key in metadata and key not in merged_args:
                merged_args[key] = metadata[key]
        if tool_name in PREVIEW_THEN_SAVE_TOOLS:
            for key in _PREVIEW_ONLY_ARGS:
                merged_args.pop(key, None)
        intent = str(metadata.get("intent") or tool_name).strip() or tool_name
        requires_confirmation = bool(metadata.get("requires_confirmation", False))
        if tool_name in PREVIEW_THEN_SAVE_TOOLS:
            requires_confirmation = True
        return ActionPlan(
            intent=intent,
            tool_name=tool_name,
            args=merged_args,
            risk_level=self.registry.get_risk_level(tool_name),
            reason="explicit tool_name in request metadata",
            requires_confirmation=requires_confirmation,
        )

    @staticmethod
    def _authorize(request: ActionRequest, plan: ActionPlan) -> tuple[bool, str]:
        if plan.risk_level != "high":
            return True, ""
        # 本地单用户工具没有登录态，高风险动作只允许进入确认，不能凭请求体里的角色直接执行。
        if request.require_confirmation and plan.requires_confirmation:
            return True, ""
        return False, "高风险动作必须经过确认后才能执行"

    def _infer_plan(self, request: ActionRequest) -> ActionPlan:
        explicit = self._plan_from_explicit_metadata(request)
        if explicit is not None:
            return explicit

        metadata = request.metadata or {}
        explicit_tool = str(metadata.get("tool_name") or "").strip()
        if explicit_tool:
            return self._no_tool_plan("unknown or invalid explicit tool_name")

        if not getattr(app_settings, "EXPERIMENTAL_ACTIONS_ALLOW_NL", False):
            return self._no_tool_plan("natural language planning disabled")

        # 只有只读的追溯可以由自然语言触发；骨架与覆盖评审需要需求文本或 ID，必须显式调用。
        if self._has_tool_intent(request.query or ""):
            return ActionPlan(
                intent="trace_matrix",
                tool_name="trace_matrix",
                args={"limit": 50},
                risk_level=self.registry.get_risk_level("trace_matrix"),
                reason="matched traceability keyword",
                requires_confirmation=False,
            )
        return self._no_tool_plan("casual or no tool keyword")

    @staticmethod
    def _build_result(
        execution_id: str,
        success: bool,
        status: str,
        message: str,
        plan: ActionPlan | None,
        tool_output: Dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ActionResult:
        return ActionResult(
            success=success,
            execution_id=execution_id,
            message=message,
            status=status,
            plan=plan,
            tool_output=tool_output,
            error=error,
        )

    @staticmethod
    def _write_audit_log(
        execution_id: str,
        request: ActionRequest,
        plan: ActionPlan,
        status: str,
        success: bool,
        tool_output: Dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        try:
            record = ToolExecutionLog.query.filter_by(execution_id=execution_id).first()
            if record is None:
                record = ToolExecutionLog(
                    execution_id=execution_id,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    query_text=request.query,
                    intent=plan.intent,
                    tool_name=plan.tool_name,
                    risk_level=plan.risk_level,
                    tool_args=json.dumps(plan.args or {}, ensure_ascii=False),
                )
            record.status = status
            record.success = success
            record.tool_output = json.dumps(tool_output, ensure_ascii=False) if tool_output is not None else None
            record.error_message = error
            db.session.add(record)
            db.session.commit()
        except Exception as log_error:
            db.session.rollback()
            logger.warning("写入实验动作审计日志失败: %s", log_error)

    @staticmethod
    def _claim_for_execution(execution_id: str) -> bool:
        """同一条待确认记录只能被执行一次：并发确认时只有改到状态的那个请求继续。"""
        try:
            claimed = ToolExecutionLog.query.filter_by(
                execution_id=execution_id, status="needs_confirmation"
            ).update({"status": "running"}, synchronize_session=False)
            db.session.commit()
        except Exception as claim_error:
            db.session.rollback()
            logger.warning("实验动作确认抢占失败: %s", claim_error)
            return False
        return claimed == 1

    def _execute_now(self, execution_id: str, request: ActionRequest, plan: ActionPlan) -> ActionResult:
        handler = self.registry.get(plan.tool_name)
        if not handler:
            message = f"未注册的工具: {plan.tool_name}"
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status="failed",
                success=False,
                tool_output=None,
                error=message,
            )
            return self._build_result(
                execution_id=execution_id,
                success=False,
                status="failed",
                message="动作执行失败",
                plan=plan,
                tool_output=None,
                error=message,
            )

        try:
            output = handler(**_accepted_args(handler, plan.args))
            tool_success = True
            if isinstance(output, dict) and "success" in output:
                tool_success = bool(output.get("success"))
            result_status = "done" if tool_success else "failed"
            tool_message = str(output.get("message", "")).strip() if isinstance(output, dict) else ""
            result_message = "动作执行成功" if tool_success else (tool_message or "动作执行失败")
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status=result_status,
                success=tool_success,
                tool_output=output,
                error=None if tool_success else str(output.get("message", "")) if isinstance(output, dict) else "tool_failed",
            )
            return self._build_result(
                execution_id=execution_id,
                success=tool_success,
                status=result_status,
                message=result_message,
                plan=plan,
                tool_output=output,
                error=None if tool_success else (str(output.get("message", "")) if isinstance(output, dict) else "tool_failed"),
            )
        except Exception as run_error:
            error_text = str(run_error)
            logger.error("实验动作执行失败: %s", error_text)
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status="failed",
                success=False,
                tool_output=None,
                error=error_text,
            )
            return self._build_result(
                execution_id=execution_id,
                success=False,
                status="failed",
                message="动作执行失败",
                plan=plan,
                tool_output=None,
                error="internal_error",
            )

    def _preview(self, plan: ActionPlan) -> Dict[str, Any]:
        handler = self.registry.get(plan.tool_name)
        args = {k: v for k, v in _accepted_args(handler, plan.args).items() if k not in _PREVIEW_ONLY_ARGS}
        try:
            output = handler(**args, save=False)
        except Exception as preview_error:  # noqa: BLE001
            logger.warning("实验动作预览失败: %s", preview_error)
            return {
                "success": False,
                "message": "预览失败",
                "message_key": "preview_failed",
                "message_params": {},
            }
        if isinstance(output, dict):
            return output
        return {"success": False, "message": "预览结果格式错误", "message_key": "preview_invalid", "message_params": {}}

    def run(self, request: ActionRequest) -> ActionResult:
        execution_id = str(uuid.uuid4())
        plan = self._infer_plan(request)
        allowed, deny_reason = self._authorize(request, plan)
        if not allowed:
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status="denied",
                success=False,
                tool_output=None,
                error=deny_reason,
            )
            return self._build_result(
                execution_id=execution_id,
                success=False,
                status="denied",
                message="无权限执行该动作",
                plan=plan,
                tool_output=None,
                error=deny_reason,
            )

        if plan.tool_name in PREVIEW_THEN_SAVE_TOOLS:
            preview = self._preview(plan)
            if not preview.get("success"):
                self._write_audit_log(
                    execution_id=execution_id,
                    request=request,
                    plan=plan,
                    status="failed",
                    success=False,
                    tool_output=preview,
                    error=str(preview.get("message", "")),
                )
                return self._build_result(
                    execution_id=execution_id,
                    success=False,
                    status="failed",
                    message=str(preview.get("message", "")).strip() or "动作执行失败",
                    plan=plan,
                    tool_output=preview,
                    error=str(preview.get("message", "")),
                )
            if not request.require_confirmation:
                self._write_audit_log(
                    execution_id=execution_id,
                    request=request,
                    plan=plan,
                    status="done",
                    success=True,
                    tool_output=preview,
                )
                return self._build_result(
                    execution_id=execution_id,
                    success=True,
                    status="done",
                    message="已生成预览，未入库",
                    plan=plan,
                    tool_output=preview,
                )
            saved_args = dict(plan.args)
            saved_args["preview_cases"] = preview.get("cases", [])
            saved_plan = ActionPlan(
                intent=plan.intent,
                tool_name=plan.tool_name,
                args=saved_args,
                risk_level=plan.risk_level,
                reason=plan.reason,
                requires_confirmation=True,
            )
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=saved_plan,
                status="needs_confirmation",
                success=True,
                tool_output=None,
            )
            return self._build_result(
                execution_id=execution_id,
                success=True,
                status="needs_confirmation",
                message="预览已生成，确认后入库",
                plan=plan,
                tool_output=preview,
            )

        if request.require_confirmation and plan.requires_confirmation:
            result = self._build_result(
                execution_id=execution_id,
                success=True,
                status="needs_confirmation",
                message="动作需要确认",
                plan=plan,
                tool_output=None,
                error=None,
            )
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status=result.status,
                success=True,
                tool_output=None,
                error=None,
            )
            return result

        if not plan.tool_name:
            hint = (
                "未识别为工具指令，未执行任何操作。"
                "请在实验工具页选择工具并填写参数。"
            )
            self._write_audit_log(
                execution_id=execution_id,
                request=request,
                plan=plan,
                status="skipped",
                success=True,
                tool_output=None,
                error=None,
            )
            return self._build_result(
                execution_id=execution_id,
                success=True,
                status="skipped",
                message=hint,
                plan=plan,
                tool_output=None,
                error=None,
            )

        return self._execute_now(execution_id=execution_id, request=request, plan=plan)

    def confirm(self, execution_id: str, metadata: Dict[str, Any] | None = None) -> ActionResult:
        record = ToolExecutionLog.query.filter_by(execution_id=str(execution_id)).first()
        if not record:
            return self._build_result(
                execution_id=str(execution_id),
                success=False,
                status="failed",
                message="执行记录不存在",
                plan=None,
                tool_output=None,
                error="execution_not_found",
            )
        if record.status != "needs_confirmation":
            return self._build_result(
                execution_id=record.execution_id,
                success=False,
                status="failed",
                message="当前状态不可确认执行",
                plan=None,
                tool_output=None,
                error=f"invalid_status:{record.status}",
            )

        args = {}
        if record.tool_args:
            try:
                args = json.loads(record.tool_args)
            except (TypeError, ValueError, json.JSONDecodeError):
                args = {}
        plan = ActionPlan(
            intent=record.intent or "",
            tool_name=record.tool_name or "",
            args=args if isinstance(args, dict) else {},
            risk_level=record.risk_level or "high",
            reason="confirmed by user",
            requires_confirmation=False,
        )
        if plan.risk_level == "high":
            confirmation = str((metadata or {}).get("confirmation_text", "")).strip()
            if confirmation != "DELETE":
                return self._build_result(
                    execution_id=record.execution_id,
                    success=False,
                    status="failed",
                    message="高风险动作需要输入 DELETE 确认",
                    plan=plan,
                    tool_output=None,
                    error="confirmation_required",
                )
        if not self._claim_for_execution(record.execution_id):
            return self._build_result(
                execution_id=record.execution_id,
                success=False,
                status="failed",
                message="当前状态不可确认执行",
                plan=None,
                tool_output=None,
                error="invalid_status:running",
            )
        if plan.tool_name in PREVIEW_THEN_SAVE_TOOLS:
            plan.args["save"] = True
        action_request = ActionRequest(
            query=record.query_text,
            session_id=record.session_id,
            user_id=record.user_id,
            require_confirmation=False,
            metadata=metadata or {},
        )
        return self._execute_now(execution_id=record.execution_id, request=action_request, plan=plan)

    def cancel(self, execution_id: str, reason: str = "") -> ActionResult:
        record = ToolExecutionLog.query.filter_by(execution_id=str(execution_id)).first()
        if not record:
            return self._build_result(
                execution_id=str(execution_id),
                success=False,
                status="failed",
                message="执行记录不存在",
                plan=None,
                tool_output=None,
                error="execution_not_found",
            )
        if record.status != "needs_confirmation":
            return self._build_result(
                execution_id=record.execution_id,
                success=False,
                status="failed",
                message="当前状态不可取消",
                plan=None,
                tool_output=None,
                error=f"invalid_status:{record.status}",
            )

        record.status = "cancelled"
        record.success = False
        record.error_message = reason or "cancelled_by_user"
        db.session.add(record)
        db.session.commit()
        return self._build_result(
            execution_id=record.execution_id,
            success=True,
            status="cancelled",
            message="动作已取消",
            plan=None,
            tool_output=None,
            error=record.error_message,
        )
