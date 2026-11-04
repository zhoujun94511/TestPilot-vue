#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Dict, List

from flask import current_app

from models.models import db
from models.models import TestCase, Requirement
from services.auth_service import current_user, stamp_ownership
from services.data_scope import apply_data_scope, can_access_record
from services.sql_query_helpers import filter_column_eq
from utils.utils_business_logic.case_id_generator import generate_case_id_from_data
from utils.utils_core.logger import get_logger

from .rule_skeleton import build_rule_cases, extract_acceptance_criteria, overlap_score

logger = get_logger(__name__)

MAX_LLM_SUPPLEMENTS = 10
MAX_SAVE_CASES = 40
COVERAGE_THRESHOLD = 0.35
_VAGUE_STEP = re.compile(r"^(?:正常|相关|按需|适当|检查|验证|测试)(?:操作|功能|内容)?$")


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (TypeError, ValueError):
            pass
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_llm_cases(raw: str) -> List[Dict[str, Any]]:
    text = str(raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except (TypeError, ValueError):
        return []
    cases = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        steps = _text_list(item.get("steps"))
        if not title or not steps:
            continue
        priority = str(item.get("priority") or "P2").strip().upper()
        cases.append({
            "rule_id": "",
            "source": "llm",
            "scenario": "",
            "title": title[:200],
            "precondition": str(item.get("precondition") or "").strip(),
            "steps": steps[:12],
            "expected_result": _text_list(item.get("expected_result"))[:8],
            "priority": priority if priority in ("P0", "P1", "P2", "P3", "P4") else "P2",
            "category": "functional",
            "test_method": str(item.get("test_method") or "").strip(),
            "module": str(item.get("module") or "").strip(),
            "tags": ["模型补充"],
            "covers": str(item.get("covers") or "").strip(),
        })
        if len(cases) >= MAX_LLM_SUPPLEMENTS:
            break
    return cases


def _llm_supplements(requirement_text: str, criteria: List[str], rule_cases: List[Dict[str, Any]],
                     count: int) -> tuple[List[Dict[str, Any]], str]:
    llm = getattr(current_app, "llm_case_generation", None)
    if llm is None:
        return [], "用例生成模型未初始化，只返回规则骨架"
    rule_titles = "\n".join(f"- {case['title']}" for case in rule_cases) or "（无）"
    criteria_text = "\n".join(f"- {item}" for item in criteria) or "（未拆出验收点）"
    prompt = (
        "你是测试设计助手。规则引擎已经写出下面这些通用用例，不要重复它们。\n"
        f"只针对需求里规则没有覆盖的业务行为，补充最多 {count} 条中文测试用例。\n"
        "不要编造需求里没有的功能。只输出 JSON 数组，每项字段："
        "title, precondition, steps(字符串数组), expected_result(字符串数组), priority(P0-P4), covers(对应的验收点原文)。\n\n"
        f"需求：\n{requirement_text}\n\n验收点：\n{criteria_text}\n\n已有规则用例：\n{rule_titles}\n"
    )
    try:
        response = llm.invoke(prompt)
    except Exception as llm_error:  # noqa: BLE001 - 模型异常不应让规则结果一起丢失
        logger.warning("规则骨架补充调用模型失败: %s", llm_error)
        return [], "模型补充失败，只返回规则骨架"
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
    supplements = _parse_llm_cases(str(content or ""))
    if not supplements:
        return [], "模型没有返回可解析的补充用例，只返回规则骨架"
    return supplements[:count], ""


def _resolve_requirement(requirement_id: str) -> tuple[Requirement | None, str]:
    req_id = str(requirement_id or "").strip()
    if not req_id:
        return None, ""
    row = Requirement.query.filter_by(req_id=req_id).first()
    if not row:
        return None, "需求不存在"
    if not can_access_record(row, "requirements"):
        return None, "没有权限访问该需求"
    return row, ""


def _save_cases(cases: List[Dict[str, Any]], requirement_id: str) -> List[Dict[str, Any]]:
    user = current_user()
    created_by = str(user.get("username")) if user and user.get("username") else "experimental"
    saved = []
    for case_data in cases[:MAX_SAVE_CASES]:
        if not isinstance(case_data, dict) or not str(case_data.get("title") or "").strip():
            continue
        tags = case_data.get("tags") or []
        row = TestCase(
            case_id=generate_case_id_from_data({"module": str(case_data.get("scenario") or "rule")}),
            title=str(case_data.get("title"))[:500],
            description="",
            precondition=str(case_data.get("precondition") or ""),
            steps=json.dumps(_text_list(case_data.get("steps")), ensure_ascii=False),
            expected_result=json.dumps(_text_list(case_data.get("expected_result")), ensure_ascii=False),
            priority=str(case_data.get("priority") or "P2"),
            category=str(case_data.get("category") or "functional"),
            test_method=str(case_data.get("test_method") or ""),
            module=str(case_data.get("module") or ""),
            tags=",".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags),
            status="draft",
            created_by=created_by,
            requirement_id=requirement_id or None,
        )
        stamp_ownership(row)
        db.session.add(row)
        db.session.flush()
        saved.append(row.to_dict())
    db.session.commit()
    return saved


def tool_rule_skeleton_cases(
    requirement_text: str = "",
    requirement_id: str = "",
    case_count: int = 5,
    use_llm: bool = True,
    preview_cases: List[Dict[str, Any]] | None = None,
    save: bool = False,
) -> Dict[str, Any]:
    """规则先写出确定性用例，模型只补缺口。save=False 只预览；确认后按预览原样入库。"""
    requirement, req_error = _resolve_requirement(requirement_id)
    if req_error:
        return {"success": False, "message": req_error, "cases": []}
    linked_req_id = requirement.req_id if requirement else ""

    if save:
        cases = preview_cases if isinstance(preview_cases, list) else []
        if not cases:
            return {"success": False, "message": "没有可保存的预览用例", "cases": []}
        try:
            saved = _save_cases(cases, linked_req_id)
        except Exception as save_error:  # noqa: BLE001
            db.session.rollback()
            logger.error("规则骨架入库失败: %s", save_error)
            return {"success": False, "message": f"保存失败: {save_error}", "cases": []}
        return {
            "success": True,
            "dry_run": False,
            "message": f"已保存 {len(saved)} 条草稿用例",
            "cases": saved,
            "count": len(saved),
            "requirement_id": linked_req_id,
        }

    text = str(requirement_text or "").strip() or (requirement.content if requirement else "")
    if not text:
        return {"success": False, "message": "请填写需求描述或选择关联需求", "cases": []}

    built = build_rule_cases(text)
    rule_cases = built["cases"]
    supplements: List[Dict[str, Any]] = []
    llm_note = ""
    supplement_count = max(1, min(_safe_int(case_count, 5), MAX_LLM_SUPPLEMENTS))
    if use_llm:
        supplements, llm_note = _llm_supplements(text, built["criteria"], rule_cases, supplement_count)
    cases = rule_cases + supplements
    if not cases:
        return {
            "success": False,
            "message": llm_note or "没有识别出搜索、登录或表单场景，也未启用模型补充",
            "cases": [],
            "scenarios": built["scenarios"],
        }
    message = f"规则写出 {len(rule_cases)} 条，模型补充 {len(supplements)} 条，确认后入库"
    return {
        "success": True,
        "dry_run": True,
        "message": message,
        "llm_note": llm_note,
        "cases": cases,
        "count": len(cases),
        "rule_count": len(rule_cases),
        "llm_count": len(supplements),
        "scenarios": built["scenarios"],
        "criteria": built["criteria"],
        "max_length": built["max_length"],
        "lock_attempts": built["lock_attempts"],
        "requirement_id": linked_req_id,
    }


def _case_text(case: Dict[str, Any]) -> str:
    parts = [str(case.get("title") or "")]
    parts.extend(_text_list(case.get("steps")))
    parts.extend(_text_list(case.get("expected_result")))
    return "\n".join(parts)


def _structure_issues(case: Dict[str, Any]) -> List[str]:
    issues = []
    title = str(case.get("title") or "").strip()
    steps = _text_list(case.get("steps"))
    expected = _text_list(case.get("expected_result"))
    if len(title) < 4:
        issues.append("title_too_short")
    if not steps:
        issues.append("steps_missing")
    elif len(steps) < 2:
        issues.append("steps_too_few")
    if steps and any(_VAGUE_STEP.match(step) for step in steps):
        issues.append("steps_vague")
    if not expected:
        issues.append("expected_missing")
    return issues


def tool_ac_coverage_review(requirement_id: str = "") -> Dict[str, Any]:
    """只读：按需求拆出的验收点对照关联用例，列出缺口和结构问题。"""
    requirement, req_error = _resolve_requirement(requirement_id)
    if req_error or requirement is None:
        return {"success": False, "message": req_error or "请选择需求"}

    criteria = extract_acceptance_criteria(requirement.content)
    query = filter_column_eq(
        apply_data_scope(TestCase.query, TestCase, "cases"),
        TestCase.requirement_id,
        str(requirement.req_id or ""),
    )
    cases = [row.to_dict() for row in query.order_by(TestCase.created_time.desc()).limit(200).all()]
    case_texts = [(case, _case_text(case)) for case in cases]

    rows = []
    for criterion in criteria:
        best_case, best_score = None, 0.0
        for case, text in case_texts:
            score = overlap_score(criterion, text)
            if score > best_score:
                best_case, best_score = case, score
        covered = best_score >= COVERAGE_THRESHOLD
        rows.append({
            "criterion": criterion,
            "covered": covered,
            "case_id": best_case.get("case_id") if best_case and covered else "",
            "case_title": best_case.get("title") if best_case and covered else "",
            "score": round(best_score, 2),
        })

    issues = [
        {"case_id": case.get("case_id"), "title": case.get("title"), "issues": found}
        for case in cases
        if (found := _structure_issues(case))
    ]
    covered_count = sum(1 for row in rows if row["covered"])
    gaps = [row["criterion"] for row in rows if not row["covered"]]
    total = len(rows)
    return {
        "success": True,
        "message": f"{total} 个验收点覆盖 {covered_count} 个，{len(issues)} 条用例结构待改",
        "requirement": {"req_id": requirement.req_id, "title": requirement.title},
        "criteria": rows,
        "gaps": gaps,
        "total": total,
        "covered_count": covered_count,
        "coverage_rate": round(covered_count / total, 2) if total else 0.0,
        "case_count": len(cases),
        "structure_issues": issues,
    }


def tool_trace_matrix(limit: int = 50) -> Dict[str, Any]:
    """只读：需求与用例双向追溯，按当前用户数据范围统计。"""
    cap = max(1, min(_safe_int(limit, 50), 200))
    requirements = (
        apply_data_scope(Requirement.query, Requirement, "requirements")
        .with_entities(Requirement.req_id, Requirement.title)
        .all()
    )
    cases = (
        apply_data_scope(TestCase.query, TestCase, "cases")
        .with_entities(TestCase.case_id, TestCase.title, TestCase.requirement_id)
        .all()
    )

    known = {row.req_id: row for row in requirements}
    linked_counts: Dict[str, int] = {}
    dangling = []
    unlinked = []
    for case in cases:
        req_id = str(case.requirement_id or "").strip()
        if not req_id:
            unlinked.append({"case_id": case.case_id, "title": case.title, "requirement_id": ""})
        elif req_id in known:
            linked_counts[req_id] = linked_counts.get(req_id, 0) + 1
        else:
            dangling.append({"case_id": case.case_id, "title": case.title, "requirement_id": req_id})

    uncovered = [
        {"req_id": row.req_id, "title": row.title, "case_count": 0}
        for row in requirements if row.req_id not in linked_counts
    ]
    covered = sorted(
        ({"req_id": req_id, "title": known[req_id].title, "case_count": count}
         for req_id, count in linked_counts.items()),
        key=lambda item: item["case_count"],
    )
    return {
        "success": True,
        "message": (
            f"{len(requirements)} 条需求中 {len(uncovered)} 条没有用例；"
            f"{len(dangling)} 条用例指向不存在的需求，{len(unlinked)} 条用例未关联需求"
        ),
        "requirement_total": len(requirements),
        "case_total": len(cases),
        "requirements_without_cases": uncovered[:cap],
        "requirements_with_cases": covered[:cap],
        "cases_with_missing_requirement": dangling[:cap],
        "cases_unlinked": unlinked[:cap],
        "counts": {
            "requirements_without_cases": len(uncovered),
            "requirements_with_cases": len(covered),
            "cases_with_missing_requirement": len(dangling),
            "cases_unlinked": len(unlinked),
        },
    }
