#!/usr/bin/python
# -*- coding: utf-8 -*-
import io

import pandas as pd
from openpyxl import Workbook, load_workbook

from services.export_service import ExportService, append_dataframe_rows, csv_safe_dataframe


def _rows():
    return [
        {'session_id': 's1', 'role': 'user', 'content': '登录怎么测', 'message_type': 'chat',
         'created_time': '2026-01-01T00:00:00+00:00', 'tokens_used': 0, 'model_name': ''},
        {'session_id': 's1', 'role': 'assistant', 'content': '先覆盖正常登录', 'message_type': 'chat',
         'created_time': '2026-01-01T00:00:01+00:00', 'tokens_used': 12, 'model_name': 'qwen'},
    ]


def test_chat_txt_export_uses_role_and_content():
    result = ExportService.export_chat_history_to_txt(_rows())
    text = result['data'].decode('utf-8')
    assert '用户:\n登录怎么测' in text
    assert '助手:\n先覆盖正常登录' in text


def test_chat_excel_export_uses_role_and_content():
    result = ExportService().export_chat_history_to_excel(_rows())
    ws = load_workbook(io.BytesIO(result['data'])).active
    header = [cell.value for cell in ws[1]]
    assert '内容' in header and '角色' in header
    values = [cell.value for cell in ws[2]]
    assert '登录怎么测' in values and '用户' in values


def test_excel_keeps_formula_like_text_as_string():
    ws = Workbook().active
    append_dataframe_rows(ws, pd.DataFrame([{'title': '=HYPERLINK("http://x")'}]))
    cell = ws['A2']
    assert cell.data_type == 's'
    assert cell.value == '=HYPERLINK("http://x")'


def test_csv_prefixes_formula_cells():
    df = csv_safe_dataframe(pd.DataFrame([{'a': '=1+1', 'b': '@SUM(A1)', 'c': 'normal', 'd': 3}]))
    row = df.iloc[0].to_dict()
    assert row['a'] == "'=1+1"
    assert row['b'] == "'@SUM(A1)"
    assert row['c'] == 'normal'
    assert row['d'] == 3
