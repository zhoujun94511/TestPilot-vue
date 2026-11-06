#!/usr/bin/python
# -*- coding: utf-8 -*-
"""项目：部门下的协作边界，只切开文档、需求和用例。知识库与 AI 聊天按部门共用，不进项目。
当前项目优先取请求头（每个标签页各自记住），没有时用登录会话里上次选的。"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app, g, has_request_context, request, session
from sqlalchemy.exc import IntegrityError

from models.auth_models import Project
from models.models import Requirement, TestCase, db
from services.auth_service import auth_required, current_user

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_NAME = '默认项目'
PROJECT_HEADER = 'X-Project-Id'
_SESSION_KEY = 'current_project_id'
_PROJECT_RESOURCES = frozenset({'cases', 'requirements'})
PROJECT_MODELS = (TestCase, Requirement)


class ProjectNameError(ValueError):
    pass


class ProjectNotEmptyError(ValueError):
    pass


_GUARD_READY: set[int] = set()
_CONTENT_GUARD = threading.RLock()
_CONTENT_DEPTH = threading.local()

# 删除项目时，库内的用例和需求靠触发器拒绝「查完又写入」；文档在文件上，靠同一把锁。
_PROJECT_GUARD_SQL = (
    """
    CREATE TRIGGER IF NOT EXISTS trg_cases_project_insert
    BEFORE INSERT ON test_cases
    FOR EACH ROW
    WHEN NEW.project_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'project_missing')
      WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_cases_project_update
    BEFORE UPDATE OF project_id ON test_cases
    FOR EACH ROW
    WHEN NEW.project_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'project_missing')
      WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_requirements_project_insert
    BEFORE INSERT ON requirements
    FOR EACH ROW
    WHEN NEW.project_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'project_missing')
      WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_requirements_project_update
    BEFORE UPDATE OF project_id ON requirements
    FOR EACH ROW
    WHEN NEW.project_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'project_missing')
      WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = NEW.project_id);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_projects_delete_blocks_rows
    BEFORE DELETE ON projects
    FOR EACH ROW
    BEGIN
      SELECT RAISE(ABORT, 'project_not_empty')
      WHERE EXISTS (SELECT 1 FROM test_cases WHERE project_id = OLD.id)
         OR EXISTS (SELECT 1 FROM requirements WHERE project_id = OLD.id);
    END
    """,
)


def ensure_projects_table() -> None:
    Project.__table__.create(bind=db.engine, checkfirst=True)


def ensure_project_delete_guards() -> None:
    """已有库加不了外键，用触发器达到同样效果：项目没了就不能再挂数据，有数据就不能删。"""
    from sqlalchemy import text

    key = id(db.engine)
    if key in _GUARD_READY:
        return
    ensure_projects_table()
    with db.engine.begin() as conn:
        names = {
            row[0]
            for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
        }
        if not {'projects', 'test_cases', 'requirements'} <= names:
            return
        for statement in _PROJECT_GUARD_SQL:
            conn.execute(text(statement))
    _GUARD_READY.add(key)


def _content_lock_path() -> Path:
    database = db.engine.url.database
    if database and database != ':memory:':
        return Path(database).with_name(Path(database).name + '.project.lock')
    return Path(os.environ.get('TEMP') or '.') / f'testpilot-project-{id(db.engine)}.lock'


def _lock_file(handle) -> None:
    if os.name == 'nt':
        import msvcrt

        handle.seek(0)
        if handle.read(1) != b'\0':
            handle.seek(0)
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        deadline = time.monotonic() + 15
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('等待项目写入锁超时')
                time.sleep(0.02)
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle) -> None:
    if os.name == 'nt':
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def project_content_lock():
    """串行化「往项目写入」和「删除项目」。进程内用线程锁，多进程再加文件锁。"""
    depth = getattr(_CONTENT_DEPTH, 'n', 0)
    if depth:
        _CONTENT_DEPTH.n = depth + 1
        try:
            yield
        finally:
            _CONTENT_DEPTH.n = depth
        return
    with _CONTENT_GUARD:
        path = _content_lock_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open('a+b')
        locked = False
        try:
            _lock_file(handle)
            locked = True
            _CONTENT_DEPTH.n = 1
            try:
                yield
            finally:
                _CONTENT_DEPTH.n = 0
        finally:
            try:
                if locked:
                    _unlock_file(handle)
            finally:
                handle.close()


def ensure_default_project(dept_id: int) -> Project:
    existing = Project.query.filter_by(dept_id=dept_id, name=DEFAULT_PROJECT_NAME).first()
    if existing:
        return existing
    project = Project(name=DEFAULT_PROJECT_NAME, dept_id=dept_id)
    db.session.add(project)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = Project.query.filter_by(dept_id=dept_id, name=DEFAULT_PROJECT_NAME).first()
        if existing:
            return existing
        raise
    return project


def backfill_projects() -> None:
    """每个部门有一个默认项目，尚未归属的需求、用例和文档挂上去。"""
    from models.auth_models import Department
    from services.auth_migrations import get_default_department_id

    ensure_projects_table()
    ensure_project_delete_guards()
    dept_ids = {row[0] for row in db.session.query(Department.id).all()}
    for model in PROJECT_MODELS:
        for (dept_id,) in db.session.query(model.dept_id).distinct().all():
            if dept_id is not None:
                dept_ids.add(int(dept_id))
    if not dept_ids:
        dept_ids.add(get_default_department_id())

    by_dept = {dept_id: ensure_default_project(dept_id).id for dept_id in dept_ids}
    fallback = by_dept[get_default_department_id()]
    changed = False
    for model in PROJECT_MODELS:
        rows = model.query.filter(model.project_id.is_(None)).all()
        for row in rows:
            row.project_id = by_dept.get(row.dept_id, fallback)
            changed = True
    if changed:
        db.session.commit()
    backfill_document_projects()


def _documents_dir() -> Optional[Path]:
    try:
        upload_root = current_app.config.get('UPLOAD_FOLDER')
    except RuntimeError:
        return None
    if not upload_root:
        return None
    return Path(upload_root) / 'documents'


def _iter_document_files():
    from services.document_meta import is_document_meta_file

    documents_dir = _documents_dir()
    if documents_dir is None or not documents_dir.is_dir():
        return
    for path in documents_dir.iterdir():
        if path.is_file() and not is_document_meta_file(path):
            yield path


def backfill_document_projects() -> None:
    """侧车说明里还没有项目的历史文档，按已分析出的需求或部门默认项目补上。"""
    for path in _iter_document_files():
        try:
            document_project_id(path)
        except Exception as exc:
            logger.warning('文档项目回填跳过 %s: %s', path.name, exc)


def document_project_id(document_path: Path, meta: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """文档所属项目。历史文档没有记录时推导一次并写回侧车说明。"""
    from services.document_meta import read_document_meta, write_document_meta

    meta = read_document_meta(document_path) if meta is None else meta
    raw = meta.get('project_id')
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    with project_content_lock():
        # 拿锁后再读一次：上传可能刚把项目写进侧车说明
        fresh = read_document_meta(document_path)
        existing = fresh.get('project_id')
        if existing is not None:
            try:
                return int(existing)
            except (TypeError, ValueError):
                pass
        project = _derive_document_project(document_path.name, fresh or meta)
        if project is None or db.session.get(Project, int(project.id)) is None:
            return None
        try:
            write_document_meta(document_path, {'project_id': project.id, 'dept_id': project.dept_id})
        except OSError as exc:
            logger.warning('文档项目写回失败 %s: %s', document_path.name, exc)
        return project.id


def _derive_document_project(filename: str, meta: Dict[str, Any]) -> Optional[Project]:
    from services.sql_query_helpers import path_name_matches

    row = (
        Requirement.query.filter(path_name_matches(Requirement.source_file, filename))
        .filter(Requirement.project_id.isnot(None))
        .order_by(Requirement.id.asc())
        .first()
    )
    if row is not None:
        project = db.session.get(Project, int(row.project_id))
        if project is not None:
            return project
    dept_id = meta.get('dept_id')
    if dept_id is None:
        from services.auth_migrations import find_default_department_id

        dept_id = find_default_department_id()
    if dept_id is None:
        return None
    return ensure_default_project(int(dept_id))


def visible_projects():
    query = Project.query.order_by(Project.dept_id.asc(), Project.id.asc())
    if not auth_required():
        return query.all()
    user = current_user()
    if not user:
        return []
    if user.get('role') == 'super_admin':
        return query.all()
    dept_id = user.get('dept_id')
    if dept_id is None:
        return []
    return query.filter(Project.dept_id == dept_id).all()


def _preferred_project_id(user: dict) -> Optional[int]:
    from services.auth_migrations import get_default_department_id

    dept_id = user.get('dept_id')
    if dept_id is None:
        dept_id = get_default_department_id()
    named = Project.query.filter_by(dept_id=dept_id, name=DEFAULT_PROJECT_NAME).first()
    if named:
        return named.id
    any_in_dept = (
        Project.query.filter_by(dept_id=dept_id).order_by(Project.id.asc()).first()
    )
    if any_in_dept:
        return any_in_dept.id
    return ensure_default_project(int(dept_id)).id


def resolve_current_project_id() -> Optional[int]:
    """请求内的当前项目。未开认证或不在请求里时不限制。"""
    if not auth_required() or not has_request_context():
        return None
    if hasattr(g, 'resolved_project_id'):
        return g.resolved_project_id
    user = current_user()
    if not user:
        g.resolved_project_id = None
        return None
    allowed = {project.id for project in visible_projects()}
    selected = _int_or_none(request.headers.get(PROJECT_HEADER))
    if selected not in allowed:
        # 请求头只代表这个标签页，不写回会话，否则多个标签页每次请求都会互相改掉新开页的默认值
        selected = _int_or_none(session.get(_SESSION_KEY))
        if selected not in allowed:
            selected = _preferred_project_id(user)
            session[_SESSION_KEY] = selected
    g.resolved_project_id = selected
    return selected


def _int_or_none(raw) -> Optional[int]:
    try:
        return int(raw) if raw not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _current_is_default_project() -> bool:
    if hasattr(g, 'current_project_is_default'):
        return g.current_project_is_default
    project_id = resolve_current_project_id()
    project = db.session.get(Project, project_id) if project_id is not None else None
    g.current_project_is_default = bool(project and project.name == DEFAULT_PROJECT_NAME)
    return g.current_project_is_default


def select_project(project_id: int) -> Project:
    project = Project.query.get(project_id)
    allowed = {item.id for item in visible_projects()}
    if project is None or project.id not in allowed:
        raise LookupError('not_found')
    if has_request_context():
        session[_SESSION_KEY] = project.id
        g.resolved_project_id = project.id
        g.pop('current_project_is_default', None)
    return project


def create_project(name: str, dept_id: Optional[int] = None) -> Project:
    cleaned = (name or '').strip()
    if not cleaned or len(cleaned) > 120:
        raise ProjectNameError('invalid_name')
    user = current_user() or {}
    role = user.get('role')
    if auth_required() and role not in ('super_admin', 'admin'):
        raise PermissionError('forbidden')
    if auth_required() and role == 'admin':
        resolved_dept = user.get('dept_id')
    elif dept_id is not None:
        resolved_dept = dept_id
    else:
        current_id = resolve_current_project_id()
        current = Project.query.get(current_id) if current_id else None
        if current is not None:
            resolved_dept = current.dept_id
        else:
            from services.auth_migrations import get_default_department_id

            resolved_dept = user.get('dept_id') or get_default_department_id()
    if resolved_dept is None:
        raise ProjectNameError('invalid_dept')
    from models.auth_models import Department

    if Department.query.get(resolved_dept) is None:
        raise ProjectNameError('invalid_dept')
    project = Project(name=cleaned, dept_id=int(resolved_dept))
    db.session.add(project)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ProjectNameError('duplicate_name')
    return project


def filter_query_by_current_project(query, model, resource: str):
    if resource not in _PROJECT_RESOURCES:
        return query
    column = getattr(model, 'project_id', None)
    if column is None:
        return query
    project_id = resolve_current_project_id()
    if project_id is None:
        return query
    if _current_is_default_project():
        return query.filter((column == project_id) | column.is_(None))
    from services.sql_query_helpers import filter_by_eq

    return filter_by_eq(query, column, project_id)


def record_in_current_project(record, resource: str) -> bool:
    """没有项目的历史记录归部门默认项目，和列表口径一致。"""
    if resource not in _PROJECT_RESOURCES:
        return True
    current = resolve_current_project_id()
    if current is None:
        return True
    project_id = getattr(record, 'project_id', None)
    if project_id is None:
        return _current_is_default_project()
    return int(project_id) == int(current)


def _project_for_management(project_id: int) -> Project:
    user = current_user() or {}
    if auth_required() and user.get('role') not in ('super_admin', 'admin'):
        raise PermissionError('forbidden')
    project = db.session.get(Project, project_id)
    if project is None or project.id not in {item.id for item in visible_projects()}:
        raise LookupError('not_found')
    return project


def rename_project(project_id: int, name: str) -> Project:
    project = _project_for_management(project_id)
    cleaned = (name or '').strip()
    if not cleaned or len(cleaned) > 120 or cleaned == DEFAULT_PROJECT_NAME:
        raise ProjectNameError('invalid_name')
    if project.name == DEFAULT_PROJECT_NAME:
        raise ProjectNameError('default_project')
    if cleaned == project.name:
        return project
    project.name = cleaned
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ProjectNameError('duplicate_name')
    return project


def delete_project(project_id: int) -> Project:
    """只删没有任何数据的项目；默认项目是历史数据的去处，不能删。
    计数和删除在同一把锁里完成。锁挡住文档写入；触发器挡住锁外面提交的用例和需求。"""
    ensure_project_delete_guards()
    with project_content_lock():
        project = _project_for_management(project_id)
        if project.name == DEFAULT_PROJECT_NAME:
            raise ProjectNameError('default_project')
        if any(project_usage(project.id).values()):
            raise ProjectNotEmptyError('not_empty')
        removed_id = project.id
        db.session.delete(project)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ProjectNotEmptyError('not_empty')
        if has_request_context():
            if _int_or_none(session.get(_SESSION_KEY)) == removed_id:
                session.pop(_SESSION_KEY, None)
            g.pop('resolved_project_id', None)
            g.pop('current_project_is_default', None)
    return project


def project_usage(project_id: int) -> Dict[str, int]:
    return projects_usage([project_id])[project_id]


def projects_usage(project_ids) -> Dict[int, Dict[str, int]]:
    """一次扫描文档目录、两次分组计数，列表页不随项目数成倍读侧车文件。"""
    from sqlalchemy import func

    from services.document_meta import read_document_meta

    ids = {int(pid) for pid in project_ids}
    usage = {pid: {'documents': 0, 'requirements': 0, 'cases': 0} for pid in ids}
    if not ids:
        return usage
    for path in _iter_document_files():
        pid = _int_or_none(read_document_meta(path).get('project_id'))
        if pid in usage:
            usage[pid]['documents'] += 1
    for key, model in (('requirements', Requirement), ('cases', TestCase)):
        rows = (
            db.session.query(model.project_id, func.count(model.id))
            .filter(model.project_id.in_(ids))
            .group_by(model.project_id)
            .all()
        )
        for pid, count in rows:
            usage[int(pid)][key] = int(count)
    return usage
