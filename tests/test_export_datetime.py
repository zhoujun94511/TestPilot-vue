#!/usr/bin/python
# -*- coding: utf-8 -*-
"""导出文件中的时间统一为北京时间，避免直接写出 UTC 的 ISO 字符串。"""

from __future__ import annotations

from datetime import datetime

from services.export_service import ExportService, format_export_datetime


def test_utc_iso_string_converted_to_beijing_time():
    assert format_export_datetime('2026-11-05T12:20:11.144192+00:00') == '2026-11-05 20:20:11'


def test_naive_datetime_treated_as_utc():
    assert format_export_datetime(datetime(2026, 11, 5, 12, 20, 11)) == '2026-11-05 20:20:11'


def test_empty_and_unparseable_values():
    assert format_export_datetime(None) == ''
    assert format_export_datetime('') == ''
    assert format_export_datetime('not-a-time') == 'not-a-time'


def test_case_row_created_time_is_beijing_time():
    case_dict = {
        'case_id': 'TC-1',
        'title': 'login',
        'created_time': '2026-11-05T12:20:11.144192+00:00',
    }
    row = ExportService._process_case_data(case_dict, case_id_mode='original', locale='zh-CN')
    headers = ExportService._case_export_headers('zh-CN')
    assert row[headers['created_time']] == '2026-11-05 20:20:11'
