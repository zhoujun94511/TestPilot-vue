#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Dict, Any
import json

from flask import current_app

from config.settings import settings
from models.models import db
from models.models import TestCase, Requirement
from services.case_service import CaseService
from services.document_service import DocumentService
from services.knowledge_service import KnowledgeService
from utils.utils_business_logic.case_id_generator import generate_case_id_from_data


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def tool_list_cases(limit: int = 10) -> Dict[str, Any]:
    """Low-risk read tool: list recent test cases."""
    query_limit = max(1, min(_safe_int(limit, 10), 50))
    rows = TestCase.query.order_by(TestCase.created_time.desc()).limit(query_limit).all()
    return {
        "items": [row.to_dict() for row in rows],
        "count": len(rows)
    }


def tool_list_requirements(limit: int = 10) -> Dict[str, Any]:
    """Low-risk read tool: list recent requirements."""
    query_limit = max(1, min(_safe_int(limit, 10), 50))
    rows = Requirement.query.order_by(Requirement.created_time.desc()).limit(query_limit).all()
    return {
        "items": [row.to_dict() for row in rows],
        "count": len(rows)
    }


def tool_delete_case(case_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """High-risk write tool: delete one test case by case_id.

    dry_run=True only previews impact and does not commit destructive change.
    """
    target_case_id = str(case_id or "").strip()
    if not target_case_id:
        return {"deleted": False, "message": "case_id不能为空"}

    row = TestCase.query.filter_by(case_id=target_case_id).first()
    if not row:
        return {"deleted": False, "message": "测试用例不存在", "case_id": target_case_id}

    if dry_run:
        return {
            "deleted": False,
            "dry_run": True,
            "message": "预演成功，等待确认后执行删除",
            "case_id": target_case_id,
            "preview": {
                "case_id": row.case_id,
                "title": row.title,
                "status": row.status,
            }
        }

    db.session.delete(row)
    db.session.commit()
    return {
        "deleted": True,
        "dry_run": False,
        "message": "测试用例删除成功",
        "case_id": target_case_id,
    }


def tool_search_knowledge(query: str, limit: int = 5) -> Dict[str, Any]:
    """Low-risk read tool: search knowledge base."""
    if not getattr(settings, "ENABLE_VECTOR_STORE", True):
        return {
            "success": False,
            "message": "向量库未启用，无法执行知识库搜索",
            "documents": [],
            "count": 0,
        }

    text = str(query or "").strip()
    if not text:
        return {"success": False, "message": "query不能为空", "documents": [], "count": 0}

    vector_db = getattr(current_app, "vector_db", None)
    if vector_db is None:
        return {"success": False, "message": "vector_db未初始化", "documents": [], "count": 0}

    service = KnowledgeService()
    result = service.search_knowledge(
        query=text,
        vector_db=vector_db,
        top_k=max(1, min(_safe_int(limit, 5), 20)),
        score_threshold=getattr(settings, "RAG_SCORE_THRESHOLD", 0.7),
    )
    docs = result.get("documents", []) if isinstance(result, dict) else []
    return {
        "success": bool(result.get("success")) if isinstance(result, dict) else False,
        "message": result.get("message", "") if isinstance(result, dict) else "",
        "documents": docs,
        "count": len(docs) if isinstance(docs, list) else 0,
    }


def tool_analyze_document_content(content: str, analysis_type: str = "requirements") -> Dict[str, Any]:
    """Low-risk tool: analyze raw document content."""
    text = str(content or "").strip()
    if not text:
        return {"success": False, "message": "content不能为空"}

    llm = getattr(current_app, "llm_requirement_analysis", None)
    if llm is None:
        return {"success": False, "message": "需求分析模型未初始化"}

    service = DocumentService()
    result = service.analyze_document_content(content=text, analysis_type=analysis_type, llm=llm)
    return result if isinstance(result, dict) else {"success": False, "message": "分析失败"}


def tool_generate_cases(requirement_text: str, case_count: int = 5, use_rag: bool = False) -> Dict[str, Any]:
    """Low-risk tool: generate test cases from requirement text."""
    req = str(requirement_text or "").strip()
    if not req:
        return {"success": False, "message": "requirement_text不能为空", "cases": [], "total": 0}

    llm = getattr(current_app, "llm_case_generation", None)
    if llm is None:
        return {"success": False, "message": "用例生成模型未初始化", "cases": [], "total": 0}

    actual_use_rag = bool(use_rag and getattr(settings, "ENABLE_VECTOR_STORE", True))
    vector_db = getattr(current_app, "vector_db", None) if actual_use_rag else None

    service = CaseService()
    result = service.generate_cases(
        requirement_text=req,
        use_rag=actual_use_rag,
        case_count=max(1, min(_safe_int(case_count, 5), 20)),
        category="functional",
        output_language="zh",
        llm=llm,
        vector_db=vector_db,
    )
    if not isinstance(result, dict):
        return {"success": False, "message": "生成失败", "cases": [], "items": [], "total": 0}
    if not result.get("success"):
        return result

    generated_cases = result.get("cases", [])
    if not isinstance(generated_cases, list):
        return {"success": False, "message": "生成结果格式错误", "cases": [], "items": [], "total": 0}

    saved_cases = []
    try:
        for case_data in generated_cases:
            if not isinstance(case_data, dict):
                continue
            test_case = TestCase(
                case_id=generate_case_id_from_data(case_data),
                display_id=case_data.get("display_id", ""),
                title=case_data.get("title", ""),
                description=case_data.get("description", ""),
                precondition=case_data.get("precondition", case_data.get("preconditions", "")),
                steps=json.dumps(case_data.get("steps", []), ensure_ascii=False),
                expected_result=case_data.get("expected_result", ""),
                priority=case_data.get("priority", "P2"),
                category=case_data.get("category", "functional"),
                test_method=case_data.get("test_method", ""),
                module=case_data.get("module", ""),
                tags=",".join(case_data.get("tags", [])) if isinstance(case_data.get("tags"), list) else str(case_data.get("tags", "")),
                status="draft",
                created_by="system"
            )
            db.session.add(test_case)
            db.session.flush()
            saved_cases.append(test_case.to_dict())
        db.session.commit()
    except Exception as save_error:
        db.session.rollback()
        return {
            "success": False,
            "message": f"生成成功但保存失败: {save_error}",
            "cases": [],
            "items": [],
            "total": 0
        }

    return {
        "success": True,
        "message": f"动作模式已生成并保存{len(saved_cases)}个测试用例",
        "cases": saved_cases,
        "items": saved_cases,
        "count": len(saved_cases),
        "total": len(saved_cases),
        "use_rag": actual_use_rag
    }

