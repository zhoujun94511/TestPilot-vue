#!/usr/bin/python
# -*- coding: utf-8 -*-
"""保存前对照打开时的更新时间，发现别人已经改过就拒绝覆盖。"""

from __future__ import annotations

from datetime import datetime, timezone


class RecordConflict(Exception):
    pass


class MissingRevision(Exception):
    """记录已有更新时间，但这次保存没有带上打开时看到的时间。"""


def _as_utc_seconds(value) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def ensure_unchanged(record, submitted) -> None:
    """记录上已有更新时间时，保存必须带上打开时的时间，并且两边一致。"""
    current = _as_utc_seconds(getattr(record, 'updated_time', None))
    if submitted is None or submitted == '':
        if current is not None:
            raise MissingRevision()
        return
    try:
        incoming = _as_utc_seconds(submitted)
    except ValueError as exc:
        raise RecordConflict() from exc
    if incoming != current:
        raise RecordConflict()
