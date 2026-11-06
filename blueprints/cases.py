#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
from typing import Any
from models.models import db, TestCase
from datetime import datetime, timezone
from werkzeug.exceptions import BadRequest
from services.case_count import clamp_cases_per_requirement
from services.case_service import CaseService
from flask import Blueprint, request, jsonify, current_app, stream_with_context
from utils.utils_business_logic.case_id_generator import generate_case_id_from_data
from utils.utils_core.api_error_handler import build_internal_error_result
from utils.utils_core import error_codes as ec
from config.settings import settings as config_settings
from services.case_field_filters import normalize_priority
from services.auth_service import stamp_ownership
from services.data_scope import apply_data_scope, can_access_record
import re

# 创建蓝图
cases_bp = Blueprint('cases', __name__)

# 初始化服务
case_service = CaseService()

_BUDGET_ERROR_CODES = {ec.TOKEN_SESSION_CALL_LIMIT, ec.TOKEN_SESSION_TOKEN_LIMIT}


def _infer_language_from_text(text: str) -> str:
    zh_count = len(re.findall(r'[\u4e00-\u9fff]', text or ''))
    en_count = len(re.findall(r'[A-Za-z]', text or ''))
    if zh_count > en_count:
        return 'zh'
    if en_count > zh_count:
        return 'en'
    return 'zh'


def _resolve_output_language(data=None, fallback_text: str = ''):
    """仅依据用户输入内容判定输出语言，不依赖界面语言/请求头。"""
    payload = data if isinstance(data, dict) else {}
    explicit = str(payload.get('output_language', '')).strip().lower()
    if explicit in ('zh', 'zh-cn', 'cn'):
        return 'zh'
    if explicit in ('en', 'en-us'):
        return 'en'
    return _infer_language_from_text(fallback_text)


def _resolve_case_generation_use_rag() -> bool:
    """
    用例生成是否启用 RAG（集中配置）：
    1) 向量库总开关 ENABLE_VECTOR_STORE 必须开启
    2) 配置中心 ENABLE_CASE_GENERATION_RAG 为 true
    """
    if not getattr(config_settings, 'ENABLE_VECTOR_STORE', True):
        return False
    try:
        from services.config_center_service import config_center_service
        value = config_center_service.get_config_value('ENABLE_CASE_GENERATION_RAG', False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes', 'on', 'enabled')
    except (ImportError, AttributeError, TypeError, ValueError, OSError, RuntimeError):
        return False


def _json_text(value):
    """把列表或字典编码一次。已经是合法 JSON 的字符串保持原样。"""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return json.dumps([], ensure_ascii=False)
        try:
            json.loads(text)
            return text
        except (json.JSONDecodeError, TypeError):
            return json.dumps(text, ensure_ascii=False)
    return json.dumps([] if value is None else value, ensure_ascii=False)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _requirement_job(req, index: int):
    if isinstance(req, dict):
        text = str(
            req.get('content') or req.get('text') or req.get('requirement') or req.get('title') or ''
        ).strip()
        req_id = str(req.get('req_id') or req.get('id') or f'req_{index + 1}')
        return req_id, text
    return f'req_{index + 1}', str(req or '').strip()


def _persist_generated_cases(case_rows, requirement_id=None):
    """只提交当前需求的用例。失败时回滚这一批，不影响已经提交的需求。"""
    saved = []
    try:
        for case_data in case_rows or []:
            if not isinstance(case_data, dict):
                continue
            test_case = _new_test_case(case_data, requirement_id or case_data.get('requirement_id'))
            db.session.add(test_case)
            saved.append(test_case)
        db.session.commit()
        return [test_case.to_dict() for test_case in saved]
    except Exception:
        db.session.rollback()
        raise


def _new_test_case(case_data, requirement_id=None):
    tags = case_data.get('tags') or []
    if isinstance(tags, str):
        tag_text = tags
    else:
        tag_text = ','.join(str(tag) for tag in tags if tag is not None)
    test_case = TestCase(
        case_id=generate_case_id_from_data(case_data),
        display_id=case_data.get('display_id') or '',
        title=case_data.get('title', ''),
        description=case_data.get('description', ''),
        precondition=case_data.get('precondition', case_data.get('preconditions', '')),
        steps=_json_text(case_data.get('steps', [])),
        expected_result=_json_text(case_data.get('expected_result', case_data.get('expected', []))),
        priority=normalize_priority(case_data.get('priority')),
        category=case_data.get('category', case_data.get('test_type', 'functional')),
        test_method=case_data.get('test_method', ''),
        module=case_data.get('module', ''),
        tags=tag_text,
        status='draft',
        created_by='system',
        requirement_id=_accessible_requirement_id(requirement_id)
    )
    stamp_ownership(test_case)
    return test_case


def _accessible_requirement_id(requirement_id):
    """只关联当前用户看得到的已有需求；批量生成里的 req_1 这类临时编号和别部门的需求一律不关联。"""
    text = str(requirement_id or '').strip()
    if not text:
        return None
    from models.models import Requirement

    requirement = Requirement.query.filter_by(req_id=text).first()
    if requirement is None or not can_access_record(requirement, 'requirements'):
        return None
    return text


def _hallucination_payload(result):
    detection = result.get('hallucination_detection') if isinstance(result, dict) else None
    if not isinstance(detection, dict):
        return None
    summary = detection.get('detection_summary') if isinstance(detection.get('detection_summary'), dict) else {}
    quality = summary.get('quality_score')
    score = round(float(quality) * 100, 1) if isinstance(quality, (int, float)) else None
    return {
        'hallucination_count': detection.get('hallucination_count', 0),
        'hallucination_rate': detection.get('hallucination_rate'),
        'avg_confidence': detection.get('avg_confidence'),
        'quality_score': quality,
        'score': score,
    }


@cases_bp.route('/generate', methods=['POST'])
def generate_test_cases():
    """生成测试用例"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        # 验证必需参数
        requirement_text = data.get('requirement_text', '').strip()
        if not requirement_text:
            raise BadRequest("需求文本不能为空")

        # 可选参数
        use_rag = _resolve_case_generation_use_rag()
        case_count = clamp_cases_per_requirement(data.get('case_count', 5), 5)
        # 优先级由AI模型自动判断，不需要用户输入
        category = data.get('category', 'functional')
        output_language = _resolve_output_language(data, requirement_text)

        # 生成用例
        result = case_service.generate_cases(
            requirement_text=requirement_text,
            use_rag=use_rag,
            case_count=case_count,
            category=category,
            output_language=output_language,
            llm=getattr(current_app, 'llm_case_generation', None),  # type: ignore 使用用例生成专用LLM
            vector_db=getattr(current_app, 'vector_db', None) if use_rag else None  # type: ignore
        )

        if result['success']:
            # 保存到数据库
            saved_cases = []
            for case_data in result['cases']:
                test_case = _new_test_case(case_data)
                db.session.add(test_case)
                saved_cases.append(test_case.to_dict())

            db.session.commit()

            payload: dict[str, Any] = {
                'success': True,
                'message': f'成功生成{len(saved_cases)}个测试用例',
                'cases': saved_cases,
                'total': len(saved_cases)
            }
            hallucination = _hallucination_payload(result)
            if hallucination:
                payload['hallucination_detection'] = hallucination
            return jsonify(payload)
        else:
            status_code = int(result.get('status_code') or 500)
            error_body = {
                'success': False,
                'message': result.get('message', '生成用例失败'),
                'error': result.get('error'),
                'error_code': result.get('error_code'),
                'retryable': bool(result.get('retryable', False))
            }
            if result.get('message_key'):
                error_body['message_key'] = result.get('message_key')
                error_body['message_params'] = result.get('message_params') or {}
            return jsonify(error_body), status_code

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"生成测试用例失败: {e}")
        error_payload = build_internal_error_result(message='生成测试用例失败')
        return jsonify({
            'success': False,
            'message': error_payload['message'],
            'error': error_payload['error'],
            'error_code': error_payload['error_code'],
            'retryable': error_payload['retryable']
        }), error_payload['status_code']


@cases_bp.route('/batch-generate', methods=['POST'])
def batch_generate_cases():
    """批量生成测试用例

    请求体 requirements 为字符串数组；Vue 批量页约定用户在 textarea 内用 ; / ； 分隔条目。
    """
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        requirements = data.get('requirements', [])
        if not requirements:
            raise BadRequest("需求列表不能为空")

        # 批量生成参数
        use_rag = _resolve_case_generation_use_rag()
        case_count_per_req = clamp_cases_per_requirement(data.get('case_count_per_req', 3), 3)
        # 并行模式在线程里跑模型调用，额度计数和数据库会话都不是线程安全的，接口只允许顺序处理
        process_mode = 'sequential'
        language_sample_text = '\n'.join([str(item) for item in requirements])
        output_language = _resolve_output_language(data, language_sample_text)

        # 执行批量生成
        result = case_service.batch_generate_cases(
            requirements=requirements,
            use_rag=use_rag,
            case_count_per_req=case_count_per_req,
            process_mode=process_mode,
            output_language=output_language,
            llm=getattr(current_app, 'llm_case_generation', None),  # type: ignore 使用用例生成专用LLM
            vector_db=getattr(current_app, 'vector_db', None) if use_rag else None  # type: ignore
        )

        if result['success']:
            all_saved_cases = []
            save_failures = 0
            for req_result in result['results']:
                if not req_result.get('success'):
                    continue
                try:
                    saved = _persist_generated_cases(
                        req_result.get('cases') or [],
                        req_result.get('requirement_id')
                    )
                    all_saved_cases.extend(saved)
                except Exception as save_error:
                    save_failures += 1
                    current_app.logger.error(f"保存需求用例失败: {save_error}")

            if not all_saved_cases:
                return jsonify({
                    'success': False,
                    'message': '批量生成完成，但用例入库失败',
                    'error': 'case_save_failed',
                    'error_code': 'case_save_failed',
                    'retryable': True
                }), 500

            message = f'批量生成完成，共生成{len(all_saved_cases)}个测试用例'
            if save_failures:
                message = f'{message}，{save_failures}个需求入库失败'
            return jsonify({
                'success': True,
                'message': message,
                'cases': all_saved_cases,
                'results': result['results'],
                'total_cases': len(all_saved_cases),
                'summary': result.get('summary', {})
            })
        else:
            status_code = int(result.get('status_code') or 500)
            return jsonify({
                'success': False,
                'message': result.get('message', '批量生成失败'),
                'error': result.get('error'),
                'error_code': result.get('error_code'),
                'retryable': bool(result.get('retryable', False))
            }), status_code

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"批量生成测试用例失败: {e}")
        error_payload = build_internal_error_result(message='批量生成测试用例失败')
        return jsonify({
            'success': False,
            'message': error_payload['message'],
            'error': error_payload['error'],
            'error_code': error_payload['error_code'],
            'retryable': error_payload['retryable']
        }), error_payload['status_code']


@cases_bp.route('/batch-generate/stream', methods=['POST'])
def batch_generate_cases_stream():
    """按需求逐条生成。每完成一条就入库并推送，失败只丢掉当前这条。"""
    try:
        data = request.get_json(silent=True) or {}
        requirements = data.get('requirements') or []
        if not isinstance(requirements, list) or not requirements:
            raise BadRequest("需求列表不能为空")

        case_count_per_req = clamp_cases_per_requirement(data.get('case_count_per_req') or 3, 3)
        max_case_num = int(getattr(config_settings, 'MAX_CASE_NUM', 50))
        if len(requirements) * case_count_per_req > max_case_num:
            return jsonify({
                'success': False,
                'message': f'批量生成用例数({len(requirements) * case_count_per_req})超过最大限制({max_case_num})',
                'error': 'validation_failed',
                'error_code': 'validation_failed',
                'retryable': False
            }), 400

        use_rag = _resolve_case_generation_use_rag()
        texts = [_requirement_job(item, index)[1] for index, item in enumerate(requirements)]
        output_language = _resolve_output_language(data, '\n'.join(texts))
        llm = getattr(current_app, 'llm_case_generation', None)
        vector_db = getattr(current_app, 'vector_db', None) if use_rag else None
        total = len(requirements)

        def generate_response():
            saved_count = 0
            failed_count = 0
            yield _sse({
                'type': 'start',
                'total': total,
                'saved_count': 0,
                'failed_count': 0
            })
            for index, req in enumerate(requirements):
                req_id, req_text = _requirement_job(req, index)
                if not req_text:
                    failed_count += 1
                    yield _sse({
                        'type': 'requirement_failed',
                        'index': index,
                        'total': total,
                        'requirement_id': req_id,
                        'saved_count': saved_count,
                        'failed_count': failed_count,
                        'message': '需求内容为空',
                        'cases': []
                    })
                    continue
                try:
                    result = case_service.generate_cases(
                        requirement_text=req_text,
                        use_rag=use_rag,
                        case_count=case_count_per_req,
                        output_language=output_language,
                        llm=llm,
                        vector_db=vector_db,
                        start_monitoring=False
                    )
                    cases = result.get('cases') if isinstance(result, dict) else None
                    if not (isinstance(result, dict) and result.get('success') and cases):
                        failed_count += 1
                        yield _sse({
                            'type': 'requirement_failed',
                            'index': index,
                            'total': total,
                            'requirement_id': req_id,
                            'saved_count': saved_count,
                            'failed_count': failed_count,
                            'message': (result.get('message') if isinstance(result, dict) else '') or '生成失败',
                            'cases': []
                        })
                        if isinstance(result, dict) and result.get('error_code') in _BUDGET_ERROR_CODES:
                            # 额度用尽后后面的需求也不会成功，直接收尾
                            failed_count += total - index - 1
                            break
                        continue
                    saved = _persist_generated_cases(cases, req_id)
                    saved_count += len(saved)
                    yield _sse({
                        'type': 'requirement_done',
                        'index': index,
                        'total': total,
                        'requirement_id': req_id,
                        'saved_count': saved_count,
                        'failed_count': failed_count,
                        'message': result.get('message') or '',
                        'cases': saved
                    })
                except Exception as item_error:
                    db.session.rollback()
                    failed_count += 1
                    current_app.logger.error(f"流式生成需求 {req_id} 失败: {item_error}")
                    yield _sse({
                        'type': 'requirement_failed',
                        'index': index,
                        'total': total,
                        'requirement_id': req_id,
                        'saved_count': saved_count,
                        'failed_count': failed_count,
                        'message': '生成失败',
                        'cases': []
                    })

            message = f'批量生成完成，共入库{saved_count}个测试用例'
            if failed_count:
                message = f'{message}，{failed_count}个需求失败，已入库的用例已保留'
            yield _sse({
                'type': 'done',
                'total': total,
                'saved_count': saved_count,
                'failed_count': failed_count,
                'message': message,
                'cases': []
            })

        return current_app.response_class(
            stream_with_context(generate_response()),
            mimetype='text/event-stream; charset=utf-8',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Content-Type': 'text/event-stream; charset=utf-8'
            }
        )
    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"流式批量生成失败: {e}")
        error_payload = build_internal_error_result(message='批量生成测试用例失败')
        return jsonify({
            'success': False,
            'message': error_payload['message'],
            'error': error_payload['error'],
            'error_code': error_payload['error_code'],
            'retryable': error_payload['retryable']
        }), error_payload['status_code']


@cases_bp.route('/list', methods=['GET'])
def list_test_cases():
    """获取测试用例列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(max(1, request.args.get('per_page', 20, type=int) or 20), 1000)
        category = request.args.get('category')
        priority = request.args.get('priority')
        status = request.args.get('status')
        search = request.args.get('search', '').strip()

        # 构建查询
        query = apply_data_scope(TestCase.query, TestCase, 'cases')

        # 添加筛选条件
        from services.case_field_filters import case_category_values, case_priority_values, filter_column_in
        from services.sql_query_helpers import filter_column_eq

        query = filter_column_in(query, TestCase.category, case_category_values(category))
        query = filter_column_in(query, TestCase.priority, case_priority_values(priority))
        query = filter_column_eq(query, TestCase.status, status)
        if search:
            query = query.filter(
                TestCase.title.contains(search, autoescape=True) |
                TestCase.description.contains(search, autoescape=True) |
                TestCase.case_id.contains(search, autoescape=True) |
                TestCase.display_id.contains(search, autoescape=True)
            )

        # 排序和分页
        query = query.order_by(TestCase.created_time.desc())
        pagination = query.paginate(  # type: ignore[attr-defined]
            page=page, per_page=per_page, error_out=False
        )

        # 转换为字典格式
        cases = [case.to_dict() for case in pagination.items]

        return jsonify({
            'success': True,
            'cases': cases,
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'total_pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'total_pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取测试用例列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取用例列表失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@cases_bp.route('/<string:case_id>', methods=['GET'])
def get_test_case(case_id):
    """获取单个测试用例详情"""
    try:
        test_case = TestCase.query.filter_by(case_id=case_id).first()
        if not test_case:
            return jsonify({
                'success': False,
                'message': '测试用例不存在'
            }), 404
        if not can_access_record(test_case, 'cases'):
            return jsonify({
                'success': False,
                'message': '没有权限访问该用例',
                'message_key': 'common.errors.http403',
            }), 403

        return jsonify({
            'success': True,
            'data': test_case.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"获取测试用例失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取测试用例失败'
        }), 500


@cases_bp.route('/<string:case_id>', methods=['PUT'])
def update_test_case(case_id):
    """更新测试用例"""
    try:
        # 先尝试按业务ID查询
        test_case = TestCase.query.filter_by(case_id=case_id).first()
        if not test_case:
            return jsonify({
                'success': False,
                'message': '测试用例不存在'
            }), 404
        if not can_access_record(test_case, 'cases'):
            return jsonify({
                'success': False,
                'message': '没有权限修改该用例',
                'message_key': 'common.errors.http403',
            }), 403

        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        from services.record_conflict import MissingRevision, RecordConflict, ensure_unchanged

        try:
            ensure_unchanged(test_case, data.get('updated_time'))
        except MissingRevision:
            return jsonify({
                'success': False,
                'code': 'VALIDATION_FAILED',
                'message': 'Request failed',
                'message_key': 'common.conflict.revisionRequired',
                'error': 'VALIDATION_FAILED',
            }), 400
        except RecordConflict:
            return jsonify({
                'success': False,
                'code': 'CONFLICT',
                'message': 'Request failed',
                'message_key': 'common.conflict.stale',
                'error': 'CONFLICT',
            }), 409

        # 更新字段
        if 'title' in data:
            title = str(data.get('title') or '').strip()
            if not title:
                raise BadRequest("用例标题不能为空")
            test_case.title = title
        if 'description' in data:
            test_case.description = data['description']
        if 'precondition' in data:
            test_case.precondition = data['precondition']
        if 'steps' in data:
            test_case.steps = _json_text(data['steps'])
        if 'expected_result' in data:
            test_case.expected_result = _json_text(data['expected_result'])
        if 'priority' in data:
            test_case.priority = normalize_priority(data['priority'], test_case.priority or 'P2')
        if 'category' in data:
            test_case.category = data['category']
        if 'tags' in data:
            test_case.tags = ','.join(data['tags']) if isinstance(data['tags'], list) else data['tags']
        if 'status' in data:
            test_case.status = data['status']
        if 'module' in data:
            test_case.module = data['module']
        if 'test_method' in data:
            test_case.test_method = data['test_method']

        test_case.updated_time = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '测试用例更新成功',
            'case': test_case.to_dict()
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新测试用例失败: {e}")
        return jsonify({
            'success': False,
            'message': '更新用例失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@cases_bp.route('/<string:case_id>', methods=['DELETE'])
def delete_test_case(case_id):
    """删除测试用例"""
    try:
        # 先尝试按业务ID查询
        test_case = TestCase.query.filter_by(case_id=case_id).first()
        if not test_case:
            return jsonify({
                'success': False,
                'message': '测试用例不存在'
            }), 404
        if not can_access_record(test_case, 'cases'):
            return jsonify({
                'success': False,
                'message': '没有权限删除该用例',
                'message_key': 'common.errors.http403',
            }), 403

        db.session.delete(test_case)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '测试用例删除成功'
        })

    except Exception as e:
        current_app.logger.error(f"删除测试用例失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除用例失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@cases_bp.route('/config', methods=['GET'])
def get_case_config():
    """获取用例生成配置选项"""
    try:
        from services.config_service import ConfigService
        
        config_service = ConfigService()
        config = config_service.get_case_generation_config()
        
        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        current_app.logger.error(f"获取用例配置失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取配置信息失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@cases_bp.route('/stats', methods=['GET'])
def get_cases_stats():
    """获取测试用例统计信息"""
    try:
        from services.stats_scope import scoped_cases_query

        scoped = scoped_cases_query()
        total_cases = scoped.count()

        status_stats = (
            scoped.with_entities(TestCase.status, db.func.count(TestCase.id))
            .group_by(TestCase.status)
            .all()
        )
        priority_stats = (
            scoped.with_entities(TestCase.priority, db.func.count(TestCase.id))
            .group_by(TestCase.priority)
            .all()
        )
        category_stats = (
            scoped.with_entities(TestCase.category, db.func.count(TestCase.id))
            .group_by(TestCase.category)
            .all()
        )

        def _bucket(rows):
            return {
                (row[0] if row[0] is not None else 'unknown'): int(row[1])
                for row in rows
            }

        return jsonify({
            'success': True,
            'stats': {
                'total_cases': total_cases,
                'by_status': _bucket(status_stats),
                'by_priority': _bucket(priority_stats),
                'by_category': _bucket(category_stats),
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取用例统计失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取统计信息失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@cases_bp.route('/generate-from-analysis', methods=['POST'])
def generate_cases_from_analysis():
    """从分析结果生成测试用例"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        # 从分析结果中提取需求信息
        requirements = data.get('requirements', [])
        use_rag = _resolve_case_generation_use_rag()
        language_sample_text = '\n'.join([str(req.get('content', '')) for req in requirements if isinstance(req, dict)])
        output_language = _resolve_output_language(data, language_sample_text)
        if not requirements:
            return jsonify({
                'success': False,
                'message': '分析结果中没有需求信息'
            }), 400
        case_count_per_req = clamp_cases_per_requirement(
            data.get('case_count_per_req', data.get('case_count', 3)),
            3
        )
        max_case_num = int(getattr(config_settings, 'MAX_CASE_NUM', 50))
        if len(requirements) * case_count_per_req > max_case_num:
            return jsonify({
                'success': False,
                'message': f'批量生成用例数({len(requirements) * case_count_per_req})超过最大限制({max_case_num})',
                'error': 'validation_failed',
                'error_code': 'validation_failed',
                'retryable': False
            }), 400

        # 为每个需求生成测试用例，完成一条就提交一条
        saved_cases = []
        failures = []
        for req in requirements:
            if not isinstance(req, dict):
                failures.append({'title': '', 'message': '需求数据格式无效'})
                continue
            result = case_service.generate_cases(
                requirement_text=req.get('content', ''),
                use_rag=use_rag,
                case_count=case_count_per_req,
                category='functional',
                output_language=output_language,
                llm=getattr(current_app, 'llm_case_generation', None),  # type: ignore 使用用例生成专用LLM
                vector_db=getattr(current_app, 'vector_db', None) if use_rag else None  # type: ignore
            )

            if result.get('success') and result.get('cases'):
                try:
                    saved_cases.extend(_persist_generated_cases(result['cases'], req.get('req_id')))
                except Exception as save_error:
                    current_app.logger.error(f"保存需求用例失败: {save_error}")
                    failures.append({
                        'req_id': req.get('req_id'),
                        'title': req.get('title', ''),
                        'message': '用例入库失败'
                    })
            else:
                failures.append({
                    'req_id': req.get('req_id'),
                    'title': req.get('title', ''),
                    'message': result.get('message', '生成失败') if isinstance(result, dict) else '生成失败'
                })

        if not saved_cases:
            return jsonify({
                'success': False,
                'message': '未能生成测试用例',
                'cases': [],
                'total': 0,
                'failed': failures,
                'failed_count': len(failures)
            }), 502

        message = f'成功生成{len(saved_cases)}个测试用例'
        if failures:
            message = f'{message}，{len(failures)}个需求生成失败'

        return jsonify({
            'success': True,
            'message': message,
            'cases': saved_cases,
            'total': len(saved_cases),
            'failed': failures,
            'failed_count': len(failures)
        })

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        current_app.logger.error(f"从分析结果生成用例失败: {e}")
        return jsonify({
            'success': False,
            'message': '生成用例失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500