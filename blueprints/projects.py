#!/usr/bin/python
# -*- coding: utf-8 -*-
"""项目列表、新建、重命名、删除和当前项目切换。"""

from __future__ import annotations

from flask import Blueprint, request

from services.auth_audit import (
    EVENT_PROJECT_CREATED,
    EVENT_PROJECT_DELETED,
    EVENT_PROJECT_RENAMED,
    log_auth_event,
)
from services.auth_service import client_ip, current_user
from services.project_service import (
    ProjectNameError,
    ProjectNotEmptyError,
    create_project,
    delete_project,
    projects_usage,
    rename_project,
    resolve_current_project_id,
    select_project,
    visible_projects,
)
from utils.auth_decorators import admin_or_above, login_required
from utils.utils_core.api_response import api_error, api_success

projects_bp = Blueprint('projects', __name__)

_NAME_ERROR_KEYS = {
    'duplicate_name': ('CONFLICT', 'common.project.duplicateName', 409),
    'default_project': ('VALIDATION_FAILED', 'common.project.defaultLocked', 400),
    'invalid_dept': ('VALIDATION_FAILED', 'common.project.invalidDept', 400),
}


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _name_error(exc: ProjectNameError):
    code, message_key, status = _NAME_ERROR_KEYS.get(
        str(exc), ('VALIDATION_FAILED', 'common.project.invalidName', 400)
    )
    return api_error(code, message='Request failed', message_key=message_key, status=status)


def _forbidden():
    return api_error('FORBIDDEN', message='Request failed', message_key='common.errors.http403', status=403)


def _not_found():
    return api_error('NOT_FOUND', message='Request failed', message_key='common.project.notFound', status=404)


def _audit(event_type: str, project, detail: str) -> None:
    actor = current_user() or {}
    log_auth_event(
        event_type,
        actor_user_id=actor.get('id'),
        username=actor.get('username'),
        ip_address=client_ip(request),
        detail=f'project={project.id};dept={project.dept_id};{detail}',
    )


@projects_bp.get('/projects')
@login_required
def list_projects():
    projects = visible_projects()
    with_usage = request.args.get('with_usage') in ('1', 'true')
    usage = projects_usage([project.id for project in projects]) if with_usage else {}
    rows = []
    for project in projects:
        row = project.to_dict()
        if with_usage:
            row['usage'] = usage[project.id]
        rows.append(row)
    return api_success({
        'projects': rows,
        'current_project_id': resolve_current_project_id(),
    })


@projects_bp.post('/projects')
@admin_or_above
def create_project_route():
    body = _body()
    dept_raw = body.get('dept_id')
    dept_id = None
    if dept_raw not in (None, ''):
        try:
            dept_id = int(dept_raw)
        except (TypeError, ValueError):
            return api_error(
                'VALIDATION_FAILED',
                message='Request failed',
                message_key='common.project.invalidDept',
                status=400,
            )
    try:
        project = create_project(str(body.get('name', '')), dept_id)
    except PermissionError:
        return _forbidden()
    except ProjectNameError as exc:
        return _name_error(exc)
    _audit(EVENT_PROJECT_CREATED, project, f'name={project.name}')
    select_project(project.id)
    return api_success({'project': project.to_dict(), 'current_project_id': project.id})


@projects_bp.patch('/projects/<int:project_id>')
@admin_or_above
def rename_project_route(project_id: int):
    try:
        project = rename_project(project_id, str(_body().get('name', '')))
    except PermissionError:
        return _forbidden()
    except LookupError:
        return _not_found()
    except ProjectNameError as exc:
        return _name_error(exc)
    _audit(EVENT_PROJECT_RENAMED, project, f'name={project.name}')
    return api_success({'project': project.to_dict()})


@projects_bp.delete('/projects/<int:project_id>')
@admin_or_above
def delete_project_route(project_id: int):
    try:
        project = delete_project(project_id)
    except PermissionError:
        return _forbidden()
    except LookupError:
        return _not_found()
    except ProjectNotEmptyError:
        return api_error(
            'CONFLICT',
            message='Request failed',
            message_key='common.project.notEmpty',
            status=409,
        )
    except ProjectNameError as exc:
        return _name_error(exc)
    _audit(EVENT_PROJECT_DELETED, project, f'name={project.name}')
    return api_success({'deleted_id': project_id, 'current_project_id': resolve_current_project_id()})


@projects_bp.put('/projects/current')
@login_required
def select_project_route():
    body = _body()
    try:
        project_id = int(body.get('project_id'))
    except (TypeError, ValueError):
        return api_error(
            'VALIDATION_FAILED',
            message='Request failed',
            message_key='common.project.required',
            status=400,
        )
    try:
        project = select_project(project_id)
    except LookupError:
        return _not_found()
    return api_success({'project': project.to_dict(), 'current_project_id': project.id})
