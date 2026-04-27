#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
import uuid
from typing import Dict, Any

from models.models import db, ToolExecutionLog
from utils.utils_core.logger import get_logger

from .registry import ToolRegistry
from .schemas import ActionPlan, ActionRequest, ActionResult
from .toolkit import (
    tool_analyze_document_content,
    tool_delete_case,
    tool_generate_cases,
    tool_list_cases,
    tool_list_requirements,
    tool_search_knowledge,
)

logger = get_logger(__name__)


class ExperimentalActionOrchestrator:
    """Experimental NL->tool orchestrator.

    This module is designed to be optional and detachable:
    - Lives under experiments/ namespace
    - Works with explicit feature flag
    - Fails closed for high-risk actions by default
    """

    def __init__(self):
        self.registry = ToolRegistry()
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.registry.register("list_cases", tool_list_cases, risk_level="low")
        self.registry.register("list_requirements", tool_list_requirements, risk_level="low")
        self.registry.register("search_knowledge", tool_search_knowledge, risk_level="low")
        self.registry.register("analyze_document_content", tool_analyze_document_content, risk_level="low")
        self.registry.register("generate_cases", tool_generate_cases, risk_level="low")
        self.registry.register("delete_case", tool_delete_case, risk_level="high")

    @staticmethod
    def _extract_case_id(text: str) -> str | None:
        match = re.search(r"(TC-[A-Za-z0-9_-]+(?:-\d+)?)", text or "", re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _is_high_risk_keyword(text: str) -> bool:
        lowered = (text or "").lower()
        return ("删除" in lowered) or ("delete" in lowered) or ("remove" in lowered)

    @staticmethod
    def _extract_limit(text: str, default: int = 10, max_limit: int = 50) -> int:
        raw = (text or "").strip().lower()
        if not raw:
            return default
        if ("所有" in raw) or ("全部" in raw) or ("all" in raw):
            return max_limit
        number_match = re.search(r"(\d{1,3})\s*(条|个|items?|cases?|requirements?)?", raw, re.IGNORECASE)
        if number_match:
            try:
                value = int(number_match.group(1))
                return max(1, min(value, max_limit))
            except (TypeError, ValueError):
                pass
        if ("最新" in raw) or ("最近" in raw) or ("latest" in raw) or ("last" in raw):
            return 1
        return default

    @staticmethod
    def _authorize(request: ActionRequest, plan: ActionPlan) -> tuple[bool, str]:
        if plan.risk_level != "high":
            return True, ""
        operator_role = str((request.metadata or {}).get("operator_role", "")).strip().lower()
        if operator_role in ("admin", "owner"):
            return True, ""
        return False, "高风险动作仅允许 admin/owner 角色执行"

    def _infer_plan(self, request: ActionRequest) -> ActionPlan:
        text = (request.query or "").strip().lower()
        raw_text = request.query or ""
        metadata = request.metadata or {}

        if self._is_high_risk_keyword(text):
            case_id = self._extract_case_id(raw_text) or str((request.metadata or {}).get("case_id", "")).strip()
            return ActionPlan(
                intent="delete_case",
                tool_name="delete_case",
                args={"case_id": case_id, "dry_run": True},
                risk_level=self.registry.get_risk_level("delete_case"),
                reason="matched delete keyword",
                requires_confirmation=True,
            )

        if ("知识库" in text) or ("knowledge" in text) or ("检索" in text) or ("搜索" in text):
            query = str(metadata.get("query", "")).strip() or raw_text
            return ActionPlan(
                intent="search_knowledge",
                tool_name="search_knowledge",
                args={"query": query, "limit": 5},
                risk_level=self.registry.get_risk_level("search_knowledge"),
                reason="matched knowledge/search keyword",
                requires_confirmation=False,
            )

        if ("分析" in text and "文档" in text) or ("analyze" in text and "document" in text):
            content = str(metadata.get("content", "")).strip()
            if not content:
                content = raw_text
            return ActionPlan(
                intent="analyze_document_content",
                tool_name="analyze_document_content",
                args={"content": content, "analysis_type": str(metadata.get("analysis_type", "requirements"))},
                risk_level=self.registry.get_risk_level("analyze_document_content"),
                reason="matched document analysis keyword",
                requires_confirmation=False,
            )

        if ("生成" in text and "用例" in text) or ("generate" in text and "case" in text):
            requirement_text = str(metadata.get("requirement_text", "")).strip() or raw_text
            return ActionPlan(
                intent="generate_cases",
                tool_name="generate_cases",
                args={
                    "requirement_text": requirement_text,
                    "case_count": int(metadata.get("case_count", 5) or 5),
                    "use_rag": bool(metadata.get("use_rag", False)),
                },
                risk_level=self.registry.get_risk_level("generate_cases"),
                reason="matched case generation keyword",
                requires_confirmation=False,
            )

        if "需求" in text or "requirement" in text:
            limit = self._extract_limit(raw_text, default=10, max_limit=50)
            return ActionPlan(
                intent="list_requirements",
                tool_name="list_requirements",
                args={"limit": limit},
                risk_level=self.registry.get_risk_level("list_requirements"),
                reason="matched requirement keyword",
                requires_confirmation=False,
            )
        limit = self._extract_limit(raw_text, default=10, max_limit=50)
        return ActionPlan(
            intent="list_cases",
            tool_name="list_cases",
            args={"limit": limit},
            risk_level=self.registry.get_risk_level("list_cases"),
            reason="default safe action",
            requires_confirmation=False,
        )

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
            record = ToolExecutionLog(
                execution_id=execution_id,
                session_id=request.session_id,
                user_id=request.user_id,
                query_text=request.query,
                intent=plan.intent,
                tool_name=plan.tool_name,
                risk_level=plan.risk_level,
                status=status,
                success=success,
                tool_args=json.dumps(plan.args or {}, ensure_ascii=False),
                tool_output=json.dumps(tool_output, ensure_ascii=False) if tool_output is not None else None,
                error_message=error,
            )
            db.session.add(record)
            db.session.commit()
        except Exception as log_error:
            db.session.rollback()
            logger.warning("写入实验动作审计日志失败: %s", log_error)

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
            output = handler(**plan.args)
            tool_success = True
            if isinstance(output, dict) and "success" in output:
                tool_success = bool(output.get("success"))
            result_status = "done" if tool_success else "failed"
            result_message = "动作执行成功" if tool_success else "动作执行失败"
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
                error=error_text,
            )

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

        if plan.risk_level == "high" and plan.tool_name == "delete_case":
            # Explicit non-confirm flow means caller accepts execution now.
            plan.args["dry_run"] = False
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
        if plan.risk_level == "high" and plan.tool_name == "delete_case":
            plan.args["dry_run"] = False
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

