#!/usr/bin/python
# -*- coding: utf-8 -*-
import io
from datetime import datetime
from werkzeug.exceptions import BadRequest
from services.export_service import ExportService
from models.models import TestCase, Requirement, ChatHistory
from flask import Blueprint, request, jsonify, current_app, send_file
import re

# 创建蓝图
export_bp = Blueprint('export', __name__)

# 初始化服务
export_service = ExportService()


def _load_full_export_rows(export_config: dict) -> dict:
    """all_cases / all_requirements 时由服务端按数据范围取全量，避免前端分页上限截断。"""
    from services.stats_scope import scoped_cases_query, scoped_requirements_query

    cfg = dict(export_config)
    if cfg.get('export_cases') and cfg.get('all_cases'):
        cfg['cases'] = [row.to_dict() for row in scoped_cases_query().order_by(TestCase.id.asc()).all()]
    if cfg.get('export_requirements') and cfg.get('all_requirements'):
        cfg['requirements'] = [
            row.to_dict() for row in scoped_requirements_query().order_by(Requirement.id.asc()).all()
        ]
    return cfg


def _scope_batch_export_config(export_config: dict) -> dict:
    """开启认证时仅保留当前用户可见的用例/需求条目。"""
    from services.auth_service import auth_required

    if not auth_required():
        return export_config

    from services.data_scope import scoped_chat_history_query
    from services.stats_scope import scoped_cases_query, scoped_requirements_query

    cfg = dict(export_config)
    if cfg.get('export_cases') and cfg.get('cases'):
        allowed_cases = {
            str(row[0])
            for row in scoped_cases_query().with_entities(TestCase.case_id).all()
            if row and row[0]
        }
        cfg['cases'] = [
            item
            for item in cfg['cases']
            if str(item.get('case_id') or item.get('id') or '') in allowed_cases
        ]
    if cfg.get('export_requirements') and cfg.get('requirements'):
        allowed_reqs = {
            str(row[0])
            for row in scoped_requirements_query().with_entities(Requirement.req_id).all()
            if row and row[0]
        }
        cfg['requirements'] = [
            item
            for item in cfg['requirements']
            if str(item.get('req_id') or item.get('id') or '') in allowed_reqs
        ]
    if cfg.get('export_chat') and cfg.get('chat_history'):
        allowed_message_ids = {
            int(row[0])
            for row in scoped_chat_history_query().with_entities(ChatHistory.id).all()
            if row and row[0] is not None
        }
        allowed_session_ids = {
            str(row[0])
            for row in scoped_chat_history_query().with_entities(ChatHistory.session_id).distinct().all()
            if row and row[0]
        }
        cfg['chat_history'] = [
            item
            for item in cfg['chat_history']
            if _batch_chat_item_allowed(item, allowed_message_ids, allowed_session_ids)
        ]
    return cfg


def _batch_chat_item_allowed(item: dict, allowed_message_ids: set[int], allowed_session_ids: set[str]) -> bool:
    if not isinstance(item, dict):
        return False
    raw_id = item.get('id')
    if raw_id is not None:
        try:
            if int(raw_id) in allowed_message_ids:
                return True
        except (TypeError, ValueError):
            pass
    session_id = str(item.get('session_id') or '').strip()
    if session_id and session_id in allowed_session_ids:
        return True
    return False


@export_bp.before_request
def _export_auth():
    from services.auth_service import auth_required, current_user
    from utils.utils_core.api_response import api_error

    if not auth_required():
        return None
    user = current_user()
    if user is None:
        return api_error(
            'UNAUTHORIZED',
            message_key='common.errors.http401',
            message='未登录或会话已过期',
            status=401,
        )
    # 已登录即可导出；用例、需求、聊天和批量导出都走数据范围，只包含当前用户可见的记录
    return None


def _export_case_query(category, priority, status, case_ids, search):
    """按业务 case_id 和列表筛选条件查询用例。"""
    from services.data_scope import apply_data_scope

    query = apply_data_scope(TestCase.query, TestCase, 'cases')
    from services.case_field_filters import case_category_values, case_priority_values, filter_column_in
    from services.sql_query_helpers import filter_column_eq

    query = filter_column_in(query, TestCase.category, case_category_values(category))
    query = filter_column_in(query, TestCase.priority, case_priority_values(priority))
    query = filter_column_eq(query, TestCase.status, status)

    raw_ids = []
    if isinstance(case_ids, list):
        raw_ids = case_ids
    elif case_ids:
        raw_ids = str(case_ids).split(',')
    ids = [str(item).strip() for item in raw_ids if str(item).strip()]
    if ids:
        query = query.filter(TestCase.case_id.in_(ids))

    term = str(search or '').strip()
    if term:
        query = query.filter(
            TestCase.title.contains(term, autoescape=True) |
            TestCase.description.contains(term, autoescape=True) |
            TestCase.case_id.contains(term, autoescape=True) |
            TestCase.display_id.contains(term, autoescape=True)
        )
    return query.order_by(TestCase.created_time.desc())


def _infer_language_from_text(text: str) -> str:
    zh_count = len(re.findall(r'[\u4e00-\u9fff]', text or ''))
    en_count = len(re.findall(r'[A-Za-z]', text or ''))
    if zh_count > en_count:
        return 'zh'
    if en_count > zh_count:
        return 'en'
    return 'zh'


def _normalize_locale_from_language(language: str) -> str:
    return 'en-US' if language == 'en' else 'zh-CN'


def _resolve_export_locale_from_cases(cases) -> str:
    """按导出内容本身推断语言，不依赖界面语言。"""
    if not cases:
        return 'zh-CN'

    sample_parts = []
    for case in cases[:20]:
        case_dict = case.to_dict() if hasattr(case, 'to_dict') else (case or {})
        sample_parts.extend([
            str(case_dict.get('title', '')),
            str(case_dict.get('description', '')),
            str(case_dict.get('precondition', '')),
            str(case_dict.get('module', '')),
            str(case_dict.get('category', '')),
            str(case_dict.get('test_method', '')),
            str(case_dict.get('tags', ''))
        ])

    language = _infer_language_from_text('\n'.join(sample_parts))
    return _normalize_locale_from_language(language)


def _resolve_template_locale() -> str:
    """模板语言优先依据用户输入文本判定。"""
    explicit = (request.args.get('output_language') or '').strip().lower()
    if explicit in ('en', 'en-us'):
        return 'en-US'
    if explicit in ('zh', 'zh-cn', 'cn'):
        return 'zh-CN'
    sample_text = (request.args.get('requirement_text') or request.args.get('text') or '').strip()
    return _normalize_locale_from_language(_infer_language_from_text(sample_text))


@export_bp.route('/cases/excel', methods=['GET', 'POST'])
def export_cases_excel():
    """导出测试用例为Excel格式"""
    try:
        # 获取参数 - 支持GET和POST
        if request.method == 'POST':
            data = request.get_json() or {}
            category = data.get('category')
            priority = data.get('priority')
            status = data.get('status')
            case_ids = data.get('case_ids')  # 可以是列表或逗号分隔的字符串
            search = data.get('search')
        else:
            category = request.args.get('category')
            priority = request.args.get('priority')
            status = request.args.get('status')
            case_ids = request.args.get('case_ids')
            search = request.args.get('search')

        cases = _export_case_query(category, priority, status, case_ids, search).all()

        if not cases:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的测试用例'
            }), 404

        # 生成Excel文件
        result = export_service.export_cases_to_excel(cases, locale=_resolve_export_locale_from_cases(cases))

        if result['success']:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_cases_{timestamp}.xlsx"

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Excel导出失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"Excel导出失败: {e}")
        return jsonify({
            'success': False,
            'message': 'Excel导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/cases/csv', methods=['GET', 'POST'])
def export_cases_csv():
    """导出测试用例为CSV格式"""
    try:
        # 获取参数 - 支持GET和POST
        if request.method == 'POST':
            data = request.get_json() or {}
            category = data.get('category')
            priority = data.get('priority')
            status = data.get('status')
            case_ids = data.get('case_ids')
            search = data.get('search')
        else:
            category = request.args.get('category')
            priority = request.args.get('priority')
            status = request.args.get('status')
            case_ids = request.args.get('case_ids')
            search = request.args.get('search')

        cases = _export_case_query(category, priority, status, case_ids, search).all()

        if not cases:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的测试用例'
            }), 404

        # 生成CSV文件
        result = export_service.export_cases_to_csv(cases, locale=_resolve_export_locale_from_cases(cases))

        if result['success']:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_cases_{timestamp}.csv"

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'CSV导出失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"CSV导出失败: {e}")
        return jsonify({
            'success': False,
            'message': 'CSV导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/cases/json', methods=['GET', 'POST'])
def export_cases_json():
    """导出测试用例为JSON格式"""
    try:
        # 获取参数 - 支持GET和POST
        if request.method == 'POST':
            data = request.get_json() or {}
            category = data.get('category')
            priority = data.get('priority')
            status = data.get('status')
            case_ids = data.get('case_ids')
            search = data.get('search')
        else:
            category = request.args.get('category')
            priority = request.args.get('priority')
            status = request.args.get('status')
            case_ids = request.args.get('case_ids')
            search = request.args.get('search')

        cases = _export_case_query(category, priority, status, case_ids, search).all()

        if not cases:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的测试用例'
            }), 404

        # 生成JSON文件
        result = export_service.export_cases_to_json(cases, locale=_resolve_export_locale_from_cases(cases))

        if result['success']:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_cases_{timestamp}.json"

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype='application/json',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'JSON导出失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"JSON导出失败: {e}")
        return jsonify({
            'success': False,
            'message': 'JSON导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/requirements/excel', methods=['GET'])
def export_requirements_excel():
    """导出需求为Excel格式"""
    try:
        # 获取筛选参数
        req_type = request.args.get('type')
        priority = request.args.get('priority')
        status = request.args.get('status')
        req_ids = request.args.get('req_ids')

        from services.sql_query_helpers import filter_column_eq
        from services.stats_scope import scoped_requirements_query

        query = scoped_requirements_query()
        query = filter_column_eq(query, Requirement.type, req_type)
        query = filter_column_eq(query, Requirement.priority, priority)
        query = filter_column_eq(query, Requirement.status, status)
        if req_ids:
            req_id_list = [req_id.strip() for req_id in req_ids.split(',') if req_id.strip()]
            if req_id_list:
                query = query.filter(Requirement.req_id.in_(req_id_list))

        # 获取数据
        requirements = query.order_by(Requirement.created_time.desc()).all()

        if not requirements:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的需求'
            }), 404

        # 生成Excel文件
        result = export_service.export_requirements_to_excel(requirements)

        if result['success']:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"requirements_{timestamp}.xlsx"

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Excel导出失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"需求Excel导出失败: {e}")
        return jsonify({
            'success': False,
            'message': '需求Excel导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/chat/history', methods=['GET'])
def export_chat_history():
    """导出聊天历史"""
    try:
        # 获取参数
        session_id = request.args.get('session_id')
        format_type = request.args.get('format', 'json')  # json, txt, excel
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        from models.models import ChatSession
        from services.chat_access import session_access_error
        from services.data_scope import scoped_chat_history_query

        if session_id:
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            denied = session_access_error(chat_session)
            if denied:
                return denied

        query = scoped_chat_history_query()

        if session_id:
            query = query.filter(ChatHistory.session_id == session_id)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(ChatHistory.created_time >= start_dt)
            except ValueError:
                raise BadRequest("开始日期格式错误")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(ChatHistory.created_time <= end_dt)
            except ValueError:
                raise BadRequest("结束日期格式错误")

        # 获取数据
        chat_history = query.order_by(ChatHistory.created_time.asc()).all()

        if not chat_history:
            return jsonify({
                'success': False,
                'message': '没有找到符合条件的聊天记录',
                'session_id': session_id
            }), 404

        # 根据格式导出
        if format_type == 'excel':
            result = export_service.export_chat_history_to_excel(chat_history)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        elif format_type == 'txt':
            result = export_service.export_chat_history_to_txt(chat_history)
            mimetype = 'text/plain'
            extension = 'txt'
        else:  # json
            result = export_service.export_chat_history_to_json(chat_history)
            mimetype = 'application/json'
            extension = 'json'

        if result['success']:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_history_{timestamp}.{extension}"

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '聊天记录导出失败'),
                'error': result.get('error')
            }), 500

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"聊天记录导出失败: {e}")
        return jsonify({
            'success': False,
            'message': '聊天记录导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/template/cases', methods=['GET'])
def get_cases_template():
    """获取测试用例导入模板"""
    try:
        template_type = request.args.get('type', 'excel')  # excel, csv

        # 生成模板
        result = export_service.generate_cases_template(template_type, locale=_resolve_template_locale())

        if result['success']:
            # 生成文件名
            template_extension = {'excel': 'xlsx', 'csv': 'csv'}.get(template_type, 'xlsx')
            filename = f"test_cases_template.{template_extension}"
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if template_type == 'excel' else 'text/csv'

            # 返回文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '模板生成失败'),
                'error': result.get('error')
            }), 500

    except Exception as e:
        current_app.logger.error(f"模板生成失败: {e}")
        return jsonify({
            'success': False,
            'message': '模板生成失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@export_bp.route('/batch', methods=['POST'])
def batch_export():
    """批量导出多种数据"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        export_config = data.get('config', {})
        if not export_config:
            raise BadRequest("导出配置不能为空")

        export_config = _scope_batch_export_config(_load_full_export_rows(export_config))

        # 执行批量导出
        result = export_service.batch_export(export_config)

        if result['success']:
            # 生成压缩文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_export_{timestamp}.zip"

            # 返回压缩文件
            return send_file(
                io.BytesIO(result['data']),
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '批量导出失败'),
                'error': result.get('error')
            }), 500

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"批量导出失败: {e}")
        return jsonify({
            'success': False,
            'message': '批量导出失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500