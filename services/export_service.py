#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import io
import json
import zipfile
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """导出服务"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()

    @staticmethod
    def _normalize_locale(locale: str = None) -> str:
        raw = (locale or 'zh-CN').lower()
        return 'en' if raw.startswith('en') else 'zh'

    @staticmethod
    def _case_export_headers(locale: str = None) -> Dict[str, str]:
        lang = ExportService._normalize_locale(locale)
        if lang == 'en':
            return {
                'case_id': 'Case ID',
                'title': 'Case Title',
                'description': 'Case Description',
                'precondition': 'Precondition',
                'steps': 'Test Steps',
                'expected_result': 'Expected Result',
                'priority': 'Priority',
                'category': 'Category',
                'module': 'Module',
                'test_method': 'Test Method',
                'tags': 'Tags',
                'status': 'Status',
                'created_time': 'Created At',
                'created_by': 'Created By',
                'requirement_id': 'Requirement ID'
            }
        return {
            'case_id': '用例ID',
            'title': '用例标题',
            'description': '用例描述',
            'precondition': '前置条件',
            'steps': '测试步骤',
            'expected_result': '预期结果',
            'priority': '优先级',
            'category': '分类',
            'module': '功能模块',
            'test_method': '测试方法',
            'tags': '标签',
            'status': '状态',
            'created_time': '创建时间',
            'created_by': '创建者',
            'requirement_id': '需求ID'
        }

    @staticmethod
    def _localize_case_field_value(field: str, value: Any, locale: str = None) -> Any:
        lang = ExportService._normalize_locale(locale)
        text = '' if value is None else str(value).strip()
        if not text:
            return value

        bilingual_map = {
            'priority': {
                'p0': {'zh': 'P0 - 最高优先级', 'en': 'P0 - Highest priority'},
                'p1': {'zh': 'P1 - 高优先级', 'en': 'P1 - High priority'},
                'p2': {'zh': 'P2 - 中优先级', 'en': 'P2 - Medium priority'},
                'p3': {'zh': 'P3 - 低优先级', 'en': 'P3 - Low priority'},
                'p4': {'zh': 'P4 - 最低优先级', 'en': 'P4 - Lowest priority'}
            },
            'status': {
                'draft': {'zh': '草稿', 'en': 'Draft'},
                'active': {'zh': '生效', 'en': 'Active'},
                'deprecated': {'zh': '已废弃', 'en': 'Deprecated'},
                '草稿': {'zh': '草稿', 'en': 'Draft'},
                '生效': {'zh': '生效', 'en': 'Active'},
                '有效': {'zh': '生效', 'en': 'Active'},
                '已废弃': {'zh': '已废弃', 'en': 'Deprecated'}
            },
            'category': {
                'functional': {'zh': '功能测试', 'en': 'Functional Testing'},
                'performance': {'zh': '性能测试', 'en': 'Performance Testing'},
                'security': {'zh': '安全测试', 'en': 'Security Testing'},
                'compatibility': {'zh': '兼容性测试', 'en': 'Compatibility Testing'},
                'usability': {'zh': '可用性测试', 'en': 'Usability Testing'},
                'integration': {'zh': '集成测试', 'en': 'Integration Testing'},
                'regression': {'zh': '回归测试', 'en': 'Regression Testing'},
                '接口测试': {'zh': '接口测试', 'en': 'API Testing'},
                '功能测试': {'zh': '功能测试', 'en': 'Functional Testing'},
                '可用性测试': {'zh': '可用性测试', 'en': 'Usability Testing'},
                '性能测试': {'zh': '性能测试', 'en': 'Performance Testing'}
            },
            'test_method': {
                '等价类划分法': {'zh': '等价类划分法', 'en': 'Equivalence Partitioning'},
                '边界值分析法': {'zh': '边界值分析法', 'en': 'Boundary Value Analysis'},
                '因果图法': {'zh': '因果图法', 'en': 'Cause-Effect Graphing'},
                '状态迁移测试': {'zh': '状态迁移测试', 'en': 'State Transition Testing'},
                'equivalence partitioning': {'zh': '等价类划分法', 'en': 'Equivalence Partitioning'},
                'boundary value analysis': {'zh': '边界值分析法', 'en': 'Boundary Value Analysis'},
                'cause-effect graphing': {'zh': '因果图法', 'en': 'Cause-Effect Graphing'},
                'state transition testing': {'zh': '状态迁移测试', 'en': 'State Transition Testing'}
            }
        }

        field_map = bilingual_map.get(field)
        if not field_map:
            return value

        key = text.lower() if field in ('priority', 'status', 'category', 'test_method') else text
        matched = field_map.get(key)
        if matched:
            return matched[lang]

        if field in ('priority', 'status'):
            compact = text.split()[0].lower()
            matched = field_map.get(compact)
            if matched:
                return matched[lang]
        return value

    @staticmethod
    def _process_case_data(case: Any, case_id_mode: str = 'sequential', case_index: int = 0, locale: str = None) -> Dict[str, Any]:
        """
        处理单个测试用例数据，统一数据格式

        Args:
            case: 测试用例对象
            case_id_mode: case_id处理模式 ('original' 原样输出, 'sequential' 顺序输出)
            case_index: 用例索引（用于顺序输出）

        Returns:
            处理后的用例数据字典
        """
        import re

        case_dict = case.to_dict() if hasattr(case, 'to_dict') else case

        # 处理case_id字段（优先使用display_id）
        display_id = case_dict.get('display_id', '')
        original_case_id = case_dict.get('case_id', '')
        
        if case_id_mode == 'sequential':
            # 顺序输出模式：TC-PLAYER-01, TC-PLAYER-02, TC-PLAYER-03...
            if display_id:
                # 使用display_id提取前缀
                prefix = display_id.split('-')[0] if '-' in display_id else 'TC'
                case_id = f"{prefix}-{case_index + 1:02d}"
            elif original_case_id:
                # 从内部ID提取前缀（去除时间戳部分）
                # 例如：TC-同屏与大地图-01-1234567890 -> TC-同屏与大地图
                parts = original_case_id.split('-')
                if len(parts) >= 3:
                    # 取前两部分作为前缀
                    prefix = '-'.join(parts[:2])
                else:
                    prefix = parts[0] if parts else 'TC'
                case_id = f"{prefix}-{case_index + 1:02d}"
            else:
                case_id = f"TC-{case_index + 1:02d}"
        else:
            # 原样输出模式（优先使用display_id）
            case_id = display_id or original_case_id

        # 处理步骤字段（JSON字符串转换为可读文本）
        steps = case_dict.get('steps', [])
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.warning(f"解析步骤JSON失败: {e}")
                steps = []

        def format_steps_with_numbers(steps_list):
            """格式化步骤，避免重复序号"""
            formatted_steps = []
            for i, step in enumerate(steps_list):
                step_str = str(step).strip()
                # 检查是否已经有序号（以数字+点+空格开头）
                if re.match(r'^\d+\.\s+', step_str):
                    formatted_steps.append(step_str)
                else:
                    formatted_steps.append(f"{i + 1}. {step_str}")
            return '\n'.join(formatted_steps)

        steps_text = format_steps_with_numbers(steps) if isinstance(steps, list) else str(steps)

        # 处理预期结果字段（JSON字符串转换为可读文本）
        expected_result = case_dict.get('expected_result', [])
        if isinstance(expected_result, str):
            try:
                expected_result = json.loads(expected_result)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.warning(f"解析预期结果JSON失败: {e}")
                expected_result = []

        def format_results_with_numbers(results_list):
            """格式化预期结果，避免重复序号"""
            formatted_results = []
            for i, result in enumerate(results_list):
                result_str = str(result).strip()
                # 检查是否已经有序号（以数字+点+空格开头）
                if re.match(r'^\d+\.\s+', result_str):
                    formatted_results.append(result_str)
                else:
                    formatted_results.append(f"{i + 1}. {result_str}")
            return '\n'.join(formatted_results)

        expected_result_text = format_results_with_numbers(expected_result) if isinstance(expected_result,
                                                                                          list) else str(
            expected_result)

        # 处理标签字段
        tags = case_dict.get('tags', [])
        if isinstance(tags, list):
            tags_text = ','.join(tags)
        else:
            tags_text = str(tags) if tags else ''

        headers = ExportService._case_export_headers(locale)
        return {
            headers['case_id']: case_id,  # 使用处理后的case_id
            headers['title']: case_dict.get('title', ''),
            headers['description']: case_dict.get('description', ''),
            headers['precondition']: case_dict.get('precondition', ''),
            headers['steps']: steps_text,
            headers['expected_result']: expected_result_text,
            headers['priority']: ExportService._localize_case_field_value('priority', case_dict.get('priority', ''), locale),
            headers['category']: ExportService._localize_case_field_value('category', case_dict.get('category', ''), locale),
            headers['module']: case_dict.get('module', ''),
            headers['test_method']: ExportService._localize_case_field_value('test_method', case_dict.get('test_method', ''), locale),
            headers['tags']: tags_text,
            headers['status']: ExportService._localize_case_field_value('status', case_dict.get('status', ''), locale),
            headers['created_time']: case_dict.get('created_time', ''),
            headers['created_by']: case_dict.get('created_by', ''),
            headers['requirement_id']: case_dict.get('requirement_id', '')
        }

    def _process_cases_data(self, cases: List[Any], case_id_mode: str = 'sequential', locale: str = None) -> List[Dict[str, Any]]:
        """
        批量处理测试用例数据

        Args:
            cases: 测试用例列表
            locale: 导出语言（如 zh-CN / en-US）
            case_id_mode: case_id处理模式 ('original' 原样输出, 'sequential' 顺序输出)

        Returns:
            处理后的用例数据列表
        """
        return [self._process_case_data(case, case_id_mode, i, locale) for i, case in enumerate(cases)]

    @staticmethod
    def _validate_cases(cases: List[Any], locale: str = None) -> Dict[str, Any]:
        """
        验证测试用例数据

        Args:
            cases: 测试用例列表
            locale: 导出语言（如 zh-CN / en-US）

        Returns:
            验证结果
        """
        _ = locale
        if not cases:
            return {
                'success': False,
                'message': '没有测试用例可导出',
                'error': 'no_cases'
            }
        return {'success': True}

    def export_cases_to_excel(self, cases: List[Any], locale: str = None) -> Dict[str, Any]:
        """
        导出测试用例到Excel

        Args:
            cases: 测试用例列表
            locale: 导出语言（如 zh-CN / en-US）

        Returns:
            导出结果
        """
        try:
            # 验证数据
            validation = self._validate_cases(cases, locale=locale)
            if not validation['success']:
                return validation

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 处理数据
            cases_data = self._process_cases_data(cases, locale=locale)
            df = pd.DataFrame(cases_data)

            # 创建Excel工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "Test Cases" if self._normalize_locale(locale) == 'en' else "测试用例"

            # 写入数据
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)

            # 设置样式
            self._style_excel_worksheet(ws, df)

            # 保存到BytesIO
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'data': output.getvalue(),
                'filename': f'测试用例_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                'export_time': elapsed_time,
                'total_cases': len(cases_data)
            }

        except Exception as e:
            logger.error(f"Excel导出失败: {e}")
            return {
                'success': False,
                'message': f'Excel导出失败: {str(e)}',
                'error': str(e)
            }

    def export_cases_to_csv(self, cases: List[Any], locale: str = None) -> Dict[str, Any]:
        """
        导出测试用例到CSV

        Args:
            cases: 测试用例列表
            locale: 导出语言（如 zh-CN / en-US）

        Returns:
            导出结果
        """
        try:
            # 验证数据
            validation = self._validate_cases(cases, locale=locale)
            if not validation['success']:
                return validation

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 处理数据
            cases_data = self._process_cases_data(cases, locale=locale)
            df = pd.DataFrame(cases_data)

            # 转换为CSV
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            csv_data = output.getvalue().encode('utf-8-sig')

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'data': csv_data,
                'filename': f'测试用例_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'export_time': elapsed_time,
                'total_cases': len(cases_data)
            }

        except Exception as e:
            logger.error(f"CSV导出失败: {e}")
            return {
                'success': False,
                'message': f'CSV导出失败: {str(e)}',
                'error': str(e)
            }

    def export_cases_to_json(self, cases: List[Any], locale: str = None) -> Dict[str, Any]:
        """
        导出测试用例到JSON

        Args:
            cases: 测试用例列表
            locale: 导出语言（如 zh-CN / en-US）

        Returns:
            导出结果
        """
        try:
            # 验证数据
            validation = self._validate_cases(cases, locale=locale)
            if not validation['success']:
                return validation

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 处理数据
            cases_data = self._process_cases_data(cases, locale=locale)

            # 转换为JSON
            json_data = json.dumps(cases_data, ensure_ascii=False, indent=2).encode('utf-8')

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'data': json_data,
                'filename': f'测试用例_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                'export_time': elapsed_time,
                'total_cases': len(cases_data)
            }

        except Exception as e:
            logger.error(f"JSON导出失败: {e}")
            return {
                'success': False,
                'message': f'JSON导出失败: {str(e)}',
                'error': str(e)
            }

    def export_requirements_to_excel(self, requirements: List[Any]) -> Dict[str, Any]:
        """
        导出需求到Excel

        Args:
            requirements: 需求列表

        Returns:
            导出结果
        """
        try:
            if not requirements:
                return {
                    'success': False,
                    'message': '没有需求可导出',
                    'error': 'no_requirements'
                }

            start_time = self.performance_monitor.start_timer()

            # 处理需求数据
            req_data = []
            for req in requirements:
                req_dict = req.to_dict() if hasattr(req, 'to_dict') else req
                req_data.append({
                    '需求ID': req_dict.get('req_id', ''),
                    '需求标题': req_dict.get('title', ''),
                    '需求内容': req_dict.get('content', ''),
                    '需求类型': req_dict.get('type', ''),
                    '优先级': req_dict.get('priority', ''),
                    '状态': req_dict.get('status', ''),
                    '来源文件': req_dict.get('source_file', ''),
                    '创建时间': req_dict.get('created_time', ''),
                    '更新时间': req_dict.get('updated_time', '')
                })

            df = pd.DataFrame(req_data)

            # 创建Excel工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "需求列表"

            # 写入数据
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)

            # 设置样式
            self._style_excel_worksheet(ws, df)

            # 保存到BytesIO
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'data': output.getvalue(),
                'filename': f'需求_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                'export_time': elapsed_time,
                'total_requirements': len(req_data)
            }

        except Exception as e:
            logger.error(f"需求Excel导出失败: {e}")
            return {
                'success': False,
                'message': f'需求Excel导出失败: {str(e)}',
                'error': str(e)
            }

    def export_chat_history_to_excel(self, chat_history: List[Any]) -> Dict[str, Any]:
        """
        导出聊天记录到Excel

        Args:
            chat_history: 聊天记录列表

        Returns:
            导出结果
        """
        try:
            if not chat_history:
                return {
                    'success': False,
                    'message': '没有聊天记录可导出',
                    'error': 'no_chat_history'
                }

            start_time = self.performance_monitor.start_timer()

            # 处理聊天记录数据
            chat_data = []
            for chat in chat_history:
                chat_dict = chat.to_dict() if hasattr(chat, 'to_dict') else chat
                chat_data.append({
                    '会话ID': chat_dict.get('session_id', ''),
                    '用户消息': chat_dict.get('user_message', ''),
                    '助手回复': chat_dict.get('assistant_message', ''),
                    '消息类型': chat_dict.get('message_type', ''),
                    'Token使用': chat_dict.get('tokens_used', 0),
                    '模型名称': chat_dict.get('model_name', ''),
                    '创建时间': chat_dict.get('created_time', '')
                })

            df = pd.DataFrame(chat_data)

            # 创建Excel工作簿
            wb = Workbook()
            ws = wb.active
            ws.title = "聊天历史"

            # 写入数据
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)

            # 设置样式
            self._style_excel_worksheet(ws, df)

            # 保存到BytesIO
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            elapsed_time = self.performance_monitor.end_timer(start_time)

            return {
                'success': True,
                'data': output.getvalue(),
                'filename': f'聊天记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                'export_time': elapsed_time,
                'total_messages': len(chat_data)
            }

        except Exception as e:
            logger.error(f"聊天记录Excel导出失败: {e}")
            return {
                'success': False,
                'message': f'聊天记录Excel导出失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def export_chat_history_to_txt(chat_history: List[Any]) -> Dict[str, Any]:
        """
        导出聊天记录到TXT

        Args:
            chat_history: 聊天记录列表

        Returns:
            导出结果
        """
        try:
            if not chat_history:
                return {
                    'success': False,
                    'message': '没有聊天记录可导出',
                    'error': 'no_chat_history'
                }

            # 生成文本格式
            lines = [
                "=" * 50,
                "TestPilot 聊天历史记录",
                f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"总记录数: {len(chat_history)}",
                "=" * 50,
                ""
            ]

            for i, chat in enumerate(chat_history, 1):
                chat_dict = chat.to_dict() if hasattr(chat, 'to_dict') else chat

                lines.append(f"【记录 {i}】")
                lines.append(f"时间: {chat_dict.get('created_time', '')}")
                lines.append(f"会话ID: {chat_dict.get('session_id', '')}")
                lines.append(f"消息类型: {chat_dict.get('message_type', '')}")
                lines.append("")
                lines.append("用户:")
                lines.append(chat_dict.get('user_message', ''))
                lines.append("")
                lines.append("助手:")
                lines.append(chat_dict.get('assistant_message', ''))
                lines.append("")
                if chat_dict.get('tokens_used'):
                    lines.append(f"Token使用: {chat_dict.get('tokens_used')}")
                if chat_dict.get('model_name'):
                    lines.append(f"模型: {chat_dict.get('model_name')}")
                lines.append("-" * 40)
                lines.append("")

            txt_content = '\n'.join(lines)

            return {
                'success': True,
                'data': txt_content.encode('utf-8'),
                'filename': f'聊天记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                'total_messages': len(chat_history)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'聊天记录TXT导出失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def export_chat_history_to_json(chat_history: List[Any]) -> Dict[str, Any]:
        """
        导出聊天记录到JSON

        Args:
            chat_history: 聊天记录列表

        Returns:
            导出结果
        """
        try:
            if not chat_history:
                return {
                    'success': False,
                    'message': '没有聊天记录可导出',
                    'error': 'no_chat_history'
                }

            # 转换为字典列表
            chat_data = []
            for chat in chat_history:
                chat_dict = chat.to_dict() if hasattr(chat, 'to_dict') else chat
                chat_data.append(chat_dict)

            # 创建导出数据结构
            export_data = {
                'export_info': {
                    'export_time': datetime.now().isoformat(),
                    'total_records': len(chat_data),
                    'format': 'json',
                    'version': '1.0'
                },
                'chat_history': chat_data
            }

            # 转换为JSON
            json_data = json.dumps(export_data, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'data': json_data.encode('utf-8'),
                'filename': f'聊天记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                'total_messages': len(chat_data)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'聊天记录JSON导出失败: {str(e)}',
                'error': str(e)
            }

    def generate_cases_template(self, template_type: str = 'excel', locale: str = None) -> Dict[str, Any]:
        """
        生成测试用例模板

        Args:
            template_type: 模板类型 (excel, csv)
            locale: 模板语言（如 zh-CN / en-US）

        Returns:
            模板生成结果
        """
        try:
            lang = self._normalize_locale(locale)
            headers = self._case_export_headers(locale)
            # 创建模板数据
            template_data = [{
                headers['case_id']: 'TC_SAMPLE_001',
                headers['title']: 'Sample test case' if lang == 'en' else '示例测试用例',
                headers['description']: 'Sample description for test case' if lang == 'en' else '这是一个示例测试用例的描述',
                headers['precondition']: 'User has logged in' if lang == 'en' else '用户已登录系统',
                headers['steps']: '1. Open page\n2. Input data\n3. Submit' if lang == 'en' else '1. 打开页面\n2. 输入数据\n3. 点击提交',
                headers['expected_result']: 'Operation succeeds with success message' if lang == 'en' else '操作成功，显示成功提示',
                headers['priority']: 'P1',
                headers['category']: 'functional',
                headers['module']: 'Auth Module' if lang == 'en' else '登录模块',
                headers['test_method']: 'Boundary Value Analysis' if lang == 'en' else '边界值分析法',
                headers['tags']: 'smoke,regression',
                headers['status']: 'draft',
                headers['created_time']: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                headers['created_by']: 'system',
                headers['requirement_id']: 'REQ_001'
            }]

            df = pd.DataFrame(template_data)

            if template_type == 'excel':
                # 创建Excel模板
                wb = Workbook()
                ws = wb.active
                ws.title = "Test Case Template" if lang == 'en' else "测试用例模板"

                # 写入数据
                for r in dataframe_to_rows(df, index=False, header=True):
                    ws.append(r)

                # 设置样式和说明
                self._style_excel_worksheet(ws, df)

                # 添加说明工作表
                ws_info = wb.create_sheet("Guide" if lang == 'en' else "使用说明")
                if lang == 'en':
                    info_text = [
                        "Test case import template guide:",
                        "",
                        "1. Case ID: unique identifier, suggested format TC_XXX_001",
                        "2. Case Title: concise and clear case title",
                        "3. Case Description: detailed case description",
                        "4. Precondition: conditions before execution",
                        "5. Test Steps: one step per line",
                        "6. Expected Result: expected behavior",
                        "7. Priority: P0/P1/P2/P3/P4",
                        "8. Category: functional/performance/security etc.",
                        "9. Module: related feature module",
                        "10. Test Method: method used for case design",
                        "11. Tags: comma-separated tags",
                        "12. Status: draft/active/deprecated",
                        "",
                        "Notes:",
                        "- Do not modify header names",
                        "- Case ID must be unique",
                        "- Steps can use line breaks"
                    ]
                else:
                    info_text = [
                        "测试用例导入模板使用说明：",
                        "",
                        "1. 用例ID: 唯一标识，格式建议为 TC_XXX_001",
                        "2. 用例标题: 简洁明了的用例名称",
                        "3. 用例描述: 详细的用例描述",
                        "4. 前置条件: 执行用例前需要满足的条件",
                        "5. 测试步骤: 具体的测试步骤，每行一个步骤",
                        "6. 预期结果: 预期的测试结果",
                        "7. 优先级: P0/P1/P2/P3/P4",
                        "8. 分类: functional/performance/security等",
                        "9. 功能模块: 所属功能模块",
                        "10. 测试方法: 使用的测试方法",
                        "11. 标签: 多个标签用逗号分隔",
                        "12. 状态: draft/active/deprecated",
                        "",
                        "注意事项：",
                        "- 请不要修改表头",
                        "- 用例ID必须唯一",
                        "- 测试步骤可以使用换行符分隔"
                    ]

                for i, text in enumerate(info_text, 1):
                    ws_info[f'A{i}'] = text

                # 保存到BytesIO
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)

                return {
                    'success': True,
                    'data': output.getvalue(),
                    'filename': f'{"test_cases_template" if lang == "en" else "测试用例模板"}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    'format': 'excel'
                }

            elif template_type == 'csv':
                # 创建CSV模板
                csv_data = df.to_csv(index=False, encoding="utf-8-sig")

                return {
                    'success': True,
                    'data': csv_data.encode("utf-8-sig"),
                    'filename': f'{"test_cases_template" if lang == "en" else "测试用例模板"}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    'format': 'csv'
                }

            else:
                return {
                    'success': False,
                    'message': f'不支持的模板类型: {template_type}',
                    'error': 'unsupported_template_type'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'模板生成失败: {str(e)}',
                'error': str(e)
            }

    def batch_export(self, export_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量导出

        Args:
            export_config: 导出配置

        Returns:
            批量导出结果
        """
        try:
            # 创建ZIP文件
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                export_count = 0

                # 导出测试用例
                if export_config.get('export_cases'):
                    cases = export_config.get('cases', [])
                    if cases:
                        for format_type in export_config.get('case_formats', ['excel']):
                            if format_type == 'excel':
                                result = self.export_cases_to_excel(cases)
                            elif format_type == 'csv':
                                result = self.export_cases_to_csv(cases)
                            elif format_type == 'json':
                                result = self.export_cases_to_json(cases)
                            else:
                                continue

                            if result['success']:
                                filename = f"test_cases.{format_type}"
                                zip_file.writestr(filename, result['data'])
                                export_count += 1

                # 导出需求
                if export_config.get('export_requirements'):
                    requirements = export_config.get('requirements', [])
                    if requirements:
                        result = self.export_requirements_to_excel(requirements)
                        if result['success']:
                            zip_file.writestr("requirements.xlsx", result['data'])
                            export_count += 1

                # 导出聊天历史
                if export_config.get('export_chat'):
                    chat_history = export_config.get('chat_history', [])
                    if chat_history:
                        for format_type in export_config.get('chat_formats', ['json']):
                            if format_type == 'excel':
                                result = self.export_chat_history_to_excel(chat_history)
                            elif format_type == 'txt':
                                result = self.export_chat_history_to_txt(chat_history)
                            elif format_type == 'json':
                                result = self.export_chat_history_to_json(chat_history)
                            else:
                                continue

                            if result['success']:
                                filename = f"chat_history.{format_type}"
                                zip_file.writestr(filename, result['data'])
                                export_count += 1

            zip_buffer.seek(0)

            return {
                'success': True,
                'data': zip_buffer.getvalue(),
                'filename': f'批量导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
                'export_count': export_count,
                'format': 'zip'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'批量导出失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def _style_excel_worksheet(ws, df):
        """设置Excel工作表样式"""
        try:
            # 使用df参数进行一些操作
            _ = df  # 标记参数已使用
            # 设置标题行样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")

            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment

            # 调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (AttributeError, TypeError):
                        pass

                # 设置合适的列宽，但不超过50
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            # 设置数据行样式
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

        except Exception as e:
            print(f"设置Excel样式失败: {e}")