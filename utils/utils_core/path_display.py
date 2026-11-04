#!/usr/bin/python
# -*- coding: utf-8 -*-
"""把返回给界面的本机绝对路径收成文件名。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_WINDOWS_ABS = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_ABS = re.compile(r"^\\\\")
_UNIX_MACHINE_ABS = re.compile(r"^/(?:home|Users|var|opt|tmp|usr|data|mnt|root|private|projectx)/")
_EMBEDDED_LOCAL_PATH = re.compile(
    r"[A-Za-z]:[\\/][^\s\"'<>|]+|\\\\[^\s\"'<>|]+|/(?:home|Users|var|opt|tmp|usr|data|mnt|root|private|projectx)/[^\s\"'<>|]+"
)


def public_file_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    if _WINDOWS_ABS.match(text) or _UNC_ABS.match(text) or _UNIX_MACHINE_ABS.match(text):
        name = Path(text.replace("\\", "/")).name
        return name or text
    return text


def redact_local_paths(value: str) -> str:
    return _EMBEDDED_LOCAL_PATH.sub(lambda match: public_file_label(match.group(0)), str(value or ""))


def _sanitize_mapping(payload: dict) -> dict:
    cleaned = dict(payload)
    for key in ("source", "file_path", "file_name", "filename"):
        raw = cleaned.get(key)
        if isinstance(raw, str) and raw.strip():
            cleaned[key] = public_file_label(raw)
    metadata = cleaned.get("metadata")
    if isinstance(metadata, dict):
        cleaned["metadata"] = _sanitize_mapping(metadata)
    if not cleaned.get("file_name"):
        label = cleaned.get("source") or cleaned.get("filename")
        if isinstance(label, str) and label.strip():
            cleaned["file_name"] = label
    return cleaned


def sanitize_search_document(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    return _sanitize_mapping(item)
