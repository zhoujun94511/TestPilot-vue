#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
from typing import Any


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _join_markdown_links(ids: list[str], base_path: str, query_key: str, max_items: int = 20) -> str:
    valid_ids = [item for item in ids if item]
    if not valid_ids:
        return "-"
    links = [f"[`{item}`]({base_path}?{query_key}={item})" for item in valid_ids[:max_items]]
    if len(valid_ids) > max_items:
        links.append(f"... 共 {len(valid_ids)} 条")
    return "、".join(links)


def _build_manage_cases_link(case_ids: list[str]) -> str:
    valid_ids = [item for item in case_ids if item]
    if not valid_ids:
        return "[用例管理](/cases/manage)"
    hids = ",".join(valid_ids[:12])
    return f"[查看并高亮新用例](/cases/manage?from=generate&hids={hids}&at=action_history)"


def _build_manage_requirements_link(req_ids: list[str]) -> str:
    valid_ids = [item for item in req_ids if item]
    if not valid_ids:
        return "[文档管理](/documents/manage)"
    rids = ",".join(valid_ids[:20])
    return f"[查看并高亮需求](/documents/manage?fromRequirements=1&rids={rids}&at=action_history)"


def _join_requirement_links(ids: list[str], max_items: int = 20) -> str:
    valid_ids = [item for item in ids if item]
    if not valid_ids:
        return "-"
    links = [
        f"[`{item}`](/documents/manage?fromRequirements=1&rids={item}&at=action_history)"
        for item in valid_ids[:max_items]
    ]
    if len(valid_ids) > max_items:
        links.append(f"... 共 {len(valid_ids)} 条")
    return "、".join(links)


def build_compact_action_history_content(action_result: Any) -> str:
    """Build compact action message for ChatHistory to avoid duplicated large payloads."""
    tool_name = action_result.plan.tool_name if action_result.plan else ""
    message = str(action_result.message or "").strip() or "动作执行完成"
    tool_output = action_result.tool_output if isinstance(action_result.tool_output, dict) else {}

    compact_payload = {
        "execution_id": action_result.execution_id,
        "status": action_result.status,
        "tool": tool_name,
    }

    if tool_name == "list_cases":
        items = _safe_list(tool_output.get("items"))
        case_ids = [
            str(item.get("case_id", "")).strip()
            for item in items
            if isinstance(item, dict) and str(item.get("case_id", "")).strip()
        ]
        compact_payload["count"] = len(items)
        compact_payload["case_ids"] = case_ids
    elif tool_name == "list_requirements":
        items = _safe_list(tool_output.get("items"))
        requirement_ids = [
            str(item.get("req_id", "")).strip()
            for item in items
            if isinstance(item, dict) and str(item.get("req_id", "")).strip()
        ]
        compact_payload["count"] = len(items)
        compact_payload["requirement_ids"] = requirement_ids
    elif tool_name == "generate_cases":
        items = _safe_list(tool_output.get("items"))
        cases = _safe_list(tool_output.get("cases"))
        merged = items or cases
        case_ids = [
            str(item.get("case_id", "")).strip()
            for item in merged
            if isinstance(item, dict) and str(item.get("case_id", "")).strip()
        ]
        compact_payload["count"] = len(merged)
        compact_payload["case_ids"] = case_ids
    else:
        if "message" in tool_output:
            compact_payload["tool_message"] = str(tool_output.get("message", "")).strip()

    lines = [message, "", f"- 执行ID: `{compact_payload.get('execution_id', '-')}`"]
    if tool_name in ("list_cases", "generate_cases"):
        ids = compact_payload.get("case_ids", [])
        id_list = ids if isinstance(ids, list) else []
        lines.append(f"- 用例数量: {compact_payload.get('count', 0)}")
        lines.append(f"- 跳转: {_build_manage_cases_link(id_list)}")
        lines.append(f"- 用例ID: {_join_markdown_links(id_list, '/cases/manage', 'case_id')}")
    elif tool_name == "list_requirements":
        ids = compact_payload.get("requirement_ids", [])
        id_list = ids if isinstance(ids, list) else []
        lines.append(f"- 需求数量: {compact_payload.get('count', 0)}")
        lines.append(f"- 跳转: {_build_manage_requirements_link(id_list)}")
        lines.append(f"- 需求ID: {_join_requirement_links(id_list)}")
    else:
        lines.append(f"- 工具: `{tool_name or '-'}`")
        if compact_payload.get("tool_message"):
            lines.append(f"- 提示: {compact_payload.get('tool_message')}")
        lines.append(f"- 摘要: `{json.dumps(compact_payload, ensure_ascii=False)}`")
    return "\n".join(lines).strip()
