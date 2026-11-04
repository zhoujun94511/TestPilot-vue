#!/usr/bin/python
# -*- coding: utf-8 -*-

from utils.utils_core.upload_storage import (
    build_versioned_storage_filename,
    resolve_display_filename,
    sanitize_upload_basename,
)


def test_sanitize_upload_basename_keeps_chinese():
    assert sanitize_upload_basename('三星折叠屏-仿真.pdf') == '三星折叠屏-仿真.pdf'


def test_build_versioned_storage_filename_pattern():
    stored, original = build_versioned_storage_filename('报告 final.md')
    assert original == '报告 final.md'
    assert stored.endswith('.md')
    parts = stored.split('_', 2)
    assert len(parts) == 3
    assert len(parts[0]) == 8
    assert len(parts[1]) == 6
    assert len(parts[2].split('_', 1)[0]) == 8


def test_resolve_display_filename_prefers_meta():
    assert resolve_display_filename('20260101_abcd1234_x.md', {'original_filename': '原文件.md'}) == '原文件.md'
