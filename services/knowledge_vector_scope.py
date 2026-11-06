#!/usr/bin/python
# -*- coding: utf-8 -*-
"""知识库向量检索：部门 pre-filter 与 chunk metadata 回填。"""

from __future__ import annotations

import ast
import logging
from typing import Any, Dict, Optional, Set

from sqlalchemy.exc import SQLAlchemyError

from models.models import RagFileRecord, db
from services.data_scope import allowed_knowledge_file_ids
from services.auth_service import current_user

logger = logging.getLogger(__name__)

_VECTOR_META_PENDING: Set[int] = set()
_PATCH_RETRY_ROUNDS = 2


def _resolve_vector_store(vector_db):
    actual = vector_db
    for _ in range(4):
        inner = getattr(actual, '_vector_db', None)
        if inner is None or inner is actual:
            break
        actual = inner
    return actual


def _metadata_scope_satisfied(
    metadatas: list,
    *,
    file_id: int,
    dept_id: int,
) -> bool:
    if not metadatas:
        return False
    for item in metadatas:
        if not isinstance(item, dict):
            return False
        if item.get('file_id') != file_id or item.get('dept_id') != dept_id:
            return False
    return True


def knowledge_vector_search_kwargs() -> Dict[str, Any]:
    """
    传给 vector_db.similarity_search* 的 kwargs。
    无认证时不限制；有限制时用 Chroma filter file_id $in。
    """
    allowed = allowed_knowledge_file_ids()
    if allowed is None:
        return {}
    if not allowed:
        return {'filter': {'file_id': {'$in': [-1]}}}
    return {'filter': {'file_id': {'$in': sorted(allowed)}}}


def dept_filter_kwargs() -> Dict[str, Any]:
    """按部门过滤（metadata 已回填 dept_id 时生效）。"""
    from services.auth_service import auth_required

    if not auth_required():
        return {}
    user = current_user()
    if not user or user.get('role') == 'super_admin':
        return {}
    dept_id = user.get('dept_id')
    if dept_id is None:
        return {'filter': {'dept_id': {'$in': [-1]}}}
    return {'filter': {'dept_id': {'$eq': int(dept_id)}}}


def merged_vector_search_kwargs() -> Dict[str, Any]:
    """优先 file_id 列表；若未开启认证则空。"""
    by_file = knowledge_vector_search_kwargs()
    if by_file:
        return by_file
    return dept_filter_kwargs()


def stamp_chunk_metadata(metadata: dict, *, file_id: Optional[int] = None, dept_id: Optional[int] = None) -> dict:
    meta = dict(metadata or {})
    user = current_user()
    if file_id is not None:
        meta['file_id'] = int(file_id)
    if dept_id is not None:
        meta['dept_id'] = int(dept_id)
    elif user and user.get('dept_id') is not None:
        meta['dept_id'] = int(user['dept_id'])
    elif dept_id is None and not (user and user.get('dept_id') is not None):
        from services.auth_migrations import get_default_department_id

        meta['dept_id'] = get_default_department_id()
    return meta


def pending_vector_metadata_file_ids() -> Set[int]:
    return set(_VECTOR_META_PENDING)


def patch_vector_metadata_for_record(record: RagFileRecord, vector_db) -> bool:
    """将 file_id / dept_id 写入已有向量 chunk metadata（上传后调用）。"""
    if not vector_db or not record or not record.ids:
        return True
    try:
        chunk_ids = ast.literal_eval(record.ids)
    except (ValueError, SyntaxError, TypeError):
        return False
    if not isinstance(chunk_ids, list) or not chunk_ids:
        return False

    resolved_dept = record.dept_id
    if resolved_dept is None:
        from services.auth_migrations import get_default_department_id

        resolved_dept = get_default_department_id()
    meta = {
        'file_id': int(record.id),
        'dept_id': int(resolved_dept),
    }
    metadatas = []
    for _ in chunk_ids:
        item = {k: v for k, v in meta.items() if v is not None}
        metadatas.append(item)

    try:
        actual = _resolve_vector_store(vector_db)
        str_ids = [str(i) for i in chunk_ids]
        if hasattr(actual, 'get'):
            try:
                existing = actual.get(ids=str_ids)
                existing_metas = existing.get('metadatas') or []
                if _metadata_scope_satisfied(
                    existing_metas,
                    file_id=int(record.id),
                    dept_id=int(resolved_dept),
                ):
                    logger.debug(
                        '向量 metadata 已满足范围字段 file=%s chunks=%s',
                        record.file_name,
                        len(chunk_ids),
                    )
                    _mark_vector_meta_synced(record)
                    return True
            except Exception as read_exc:
                logger.debug('读取向量 metadata 跳过 file=%s: %s', record.file_name, read_exc)

        if hasattr(actual, 'update'):
            actual.update(ids=str_ids, metadatas=metadatas)
            logger.info('已回填向量 metadata: file=%s chunks=%s', record.file_name, len(chunk_ids))
            _mark_vector_meta_synced(record)
            return True

        collection = getattr(actual, '_collection', None)
        if collection is not None and hasattr(collection, 'update'):
            collection.update(ids=str_ids, metadatas=metadatas)
            logger.info('已回填向量 metadata: file=%s chunks=%s', record.file_name, len(chunk_ids))
            _mark_vector_meta_synced(record)
            return True

        logger.warning('向量库不支持 metadata 更新 file=%s backend=%s', record.file_name, type(actual).__name__)
        _mark_vector_meta_pending(record)
        return False
    except Exception as exc:
        logger.warning('向量 metadata 回填失败 file=%s: %s', record.file_name, exc)
        _mark_vector_meta_pending(record)
        return False


def _mark_vector_meta_synced(record: RagFileRecord) -> None:
    _VECTOR_META_PENDING.discard(int(record.id))
    if getattr(record, 'vector_meta_pending', 0):
        record.vector_meta_pending = 0
        _commit_vector_meta_flag(record)


def _mark_vector_meta_pending(record: RagFileRecord) -> None:
    _VECTOR_META_PENDING.add(int(record.id))
    if hasattr(record, 'vector_meta_pending'):
        record.vector_meta_pending = 1
        _commit_vector_meta_flag(record)


def _commit_vector_meta_flag(record: RagFileRecord) -> None:
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        logger.debug('vector_meta_pending 提交失败 file=%s: %s', record.file_name, exc)
        try:
            db.session.rollback()
        except SQLAlchemyError:
            pass


def _collect_pending_file_ids() -> Set[int]:
    pending = set(_VECTOR_META_PENDING)
    try:
        rows = RagFileRecord.query.filter(RagFileRecord.vector_meta_pending == 1).all()
        pending.update(int(row.id) for row in rows)
    except (AttributeError, OSError, RuntimeError, ValueError) as exc:
        logger.debug('读取 vector_meta_pending 列失败（可能尚未迁移）: %s', exc)
    return pending


def retry_pending_vector_metadata(vector_db) -> int:
    """重试此前失败的 metadata 回填，返回仍失败的数量。"""
    if vector_db is None:
        return 0
    pending_ids = _collect_pending_file_ids()
    if not pending_ids:
        return 0
    still_failed: Set[int] = set()
    for file_id in pending_ids:
        row = RagFileRecord.query.get(file_id)
        if not row:
            _VECTOR_META_PENDING.discard(file_id)
            continue
        if patch_vector_metadata_for_record(row, vector_db):
            continue
        still_failed.add(file_id)
    _VECTOR_META_PENDING.clear()
    _VECTOR_META_PENDING.update(still_failed)
    return len(still_failed)


def backfill_all_knowledge_vector_metadata(vector_db) -> int:
    """启动时：为所有 active 文件回填向量 metadata（含有限重试）。"""
    if vector_db is None:
        return 0
    ok_count = 0
    rows = RagFileRecord.query.filter(RagFileRecord.status == 'active').all()
    for row in rows:
        if patch_vector_metadata_for_record(row, vector_db):
            ok_count += 1

    for round_idx in range(_PATCH_RETRY_ROUNDS):
        pending_before = len(_VECTOR_META_PENDING)
        if pending_before == 0:
            break
        failed = retry_pending_vector_metadata(vector_db)
        logger.info(
            '向量 metadata 回填重试 round=%s pending_before=%s still_failed=%s',
            round_idx + 1,
            pending_before,
            failed,
        )

    if _VECTOR_META_PENDING:
        logger.error(
            '向量 metadata 回填最终失败 file_ids=%s（检索仍依赖结果层 filter）',
            sorted(_VECTOR_META_PENDING),
        )
    return ok_count
