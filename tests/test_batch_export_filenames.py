#!/usr/bin/python
# -*- coding: utf-8 -*-
"""批量导出 ZIP 内文件名必须用真实后缀。"""

from __future__ import annotations

import io
import zipfile

from services.export_service import ExportService


def test_file_extension_maps_excel_to_xlsx():
    assert ExportService.file_extension('excel') == 'xlsx'
    assert ExportService.file_extension('csv') == 'csv'
    assert ExportService.file_extension('json') == 'json'
    assert ExportService.file_extension('txt') == 'txt'


def test_batch_zip_uses_real_extensions(monkeypatch):
    service = ExportService()
    ok = {'success': True, 'data': b'x'}
    monkeypatch.setattr(service, 'export_cases_to_excel', lambda cases: ok)
    monkeypatch.setattr(service, 'export_cases_to_csv', lambda cases: ok)
    monkeypatch.setattr(service, 'export_cases_to_json', lambda cases: ok)
    monkeypatch.setattr(service, 'export_chat_history_to_excel', lambda rows: ok)
    monkeypatch.setattr(service, 'export_chat_history_to_txt', lambda rows: ok)
    monkeypatch.setattr(service, 'export_chat_history_to_json', lambda rows: ok)

    result = service.batch_export({
        'export_cases': True,
        'cases': [object()],
        'case_formats': ['excel', 'csv', 'json'],
        'export_chat': True,
        'chat_history': [object()],
        'chat_formats': ['excel', 'txt', 'json'],
    })

    assert result['success']
    names = set(zipfile.ZipFile(io.BytesIO(result['data'])).namelist())
    assert names == {
        'test_cases.xlsx', 'test_cases.csv', 'test_cases.json',
        'chat_history.xlsx', 'chat_history.txt', 'chat_history.json',
    }
    assert not any(name.endswith('.excel') for name in names)
