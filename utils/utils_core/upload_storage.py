#!/usr/bin/python
# -*- coding: utf-8 -*-
"""上传文件磁盘命名：需求文档与知识库共用规则。"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime


def sanitize_upload_basename(input_filename: str, *, default_stem: str = 'document') -> str:
    """保留中文的安全文件名（含扩展名）。"""
    name, ext = os.path.splitext(input_filename or '')
    safe_name = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', name)
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    if not safe_name:
        safe_name = default_stem
    return safe_name + ext


def build_versioned_storage_filename(
    original_filename: str,
    *,
    default_stem: str = 'document',
) -> tuple[str, str]:
    """
    生成磁盘存储名：{yyyyMMdd_HHmmss}_{uuid8}_{安全原名}

    Returns:
        (stored_filename, original_filename)
    """
    original = (original_filename or '').replace('\\', '/').split('/')[-1].strip()
    if not original:
        original = f'{default_stem}.bin'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    short_id = str(uuid.uuid4())[:8]
    safe_original = sanitize_upload_basename(original, default_stem=default_stem)
    stored = f'{timestamp}_{short_id}_{safe_original}'
    file_ext = ''
    if '.' in original:
        file_ext = '.' + original.rsplit('.', 1)[1].lower()
    if file_ext and not stored.lower().endswith(file_ext):
        stored = os.path.splitext(stored)[0] + file_ext
    return stored, original


def resolve_display_filename(stored_filename: str, meta: dict | None) -> str:
    """列表/界面展示名：优先 meta.original_filename。"""
    if meta and meta.get('original_filename'):
        return str(meta['original_filename'])
    return stored_filename
