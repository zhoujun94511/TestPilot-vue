#!/usr/bin/python
# -*- coding: utf-8 -*-
"""文档侧车元数据（上传/分析时选择的 analysis_type 等）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

VALID_ANALYSIS_TYPES = frozenset({'requirements', 'test_points', 'business_rules', 'comprehensive'})


def normalize_analysis_type(value: Optional[str]) -> str:
    key = str(value or '').strip().lower()
    if key in ('test_point',):
        return 'test_points'
    if key in ('business_rule',):
        return 'business_rules'
    if key in VALID_ANALYSIS_TYPES:
        return key
    return 'requirements'


def meta_path_for_document(document_path: Path) -> Path:
    return document_path.parent / f'{document_path.name}.meta.json'


def is_document_meta_file(path: Path) -> bool:
    return path.is_file() and path.name.endswith('.meta.json')


def read_document_meta(document_path: Path) -> Dict[str, Any]:
    meta_path = meta_path_for_document(document_path)
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def stamp_document_ownership(document_path: Path | str) -> Dict[str, Any]:
    """上传时写入 project_id / dept_id / owner_user_id（开启认证且已登录）。部门跟项目走。
    和删除项目共用一把锁：写之前再确认项目还在，避免写到刚删掉的项目上。"""
    from services.auth_service import auth_required, current_user
    from services.project_service import project_content_lock

    path = Path(document_path)
    if not auth_required():
        return read_document_meta(path)
    user = current_user()
    if not user:
        return read_document_meta(path)
    with project_content_lock():
        project = _upload_project(user)
        if project is not None and _project_row_exists(int(project.id)):
            dept_id = project.dept_id
            project_id = int(project.id)
        else:
            project_id = None
            dept_id = user.get('dept_id')
        patch: Dict[str, Any] = {}
        user_id = user.get('id')
        if project_id is not None:
            patch['project_id'] = project_id
        if dept_id is not None:
            patch['dept_id'] = int(dept_id)
        if user_id is not None:
            patch['owner_user_id'] = int(user_id)
        if not patch:
            return read_document_meta(path)
        return write_document_meta(path, patch)


def _project_row_exists(project_id: int) -> bool:
    from models.auth_models import Project
    from models.models import db

    return db.session.get(Project, project_id) is not None


def _upload_project(user: Dict[str, Any]):
    from models.auth_models import Project
    from models.models import db
    from services.project_service import ensure_default_project, resolve_current_project_id

    project_id = resolve_current_project_id()
    if project_id is not None:
        project = db.session.get(Project, project_id)
        if project is not None:
            return project
    if user.get('dept_id') is not None:
        return ensure_default_project(int(user['dept_id']))
    return None


def write_document_meta(document_path: Path, patch: Dict[str, Any]) -> Dict[str, Any]:
    meta = read_document_meta(document_path)
    meta.update(patch)
    meta_path = meta_path_for_document(document_path)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return meta


def persist_document_analysis_type(
    document_path: Path | str,
    analysis_type: str,
    *,
    status: str = 'analyzed'
) -> Dict[str, Any]:
    path = Path(document_path)
    return write_document_meta(
        path,
        {
            'analysis_type': normalize_analysis_type(analysis_type),
            'analysis_status': status,
            'analyzed_at': datetime.now(timezone.utc).isoformat()
        }
    )


def resolve_stored_analysis_type(document_path: Path) -> Optional[str]:
    meta = read_document_meta(document_path)
    if 'analysis_type' not in meta:
        return None
    return normalize_analysis_type(meta.get('analysis_type'))


def document_matches_analysis_filter(stored_type: Optional[str], filter_type: str) -> bool:
    normalized_filter = normalize_analysis_type(filter_type)
    if normalized_filter == 'comprehensive':
        return True
    if stored_type is None:
        return False
    return normalize_analysis_type(stored_type) == normalized_filter
