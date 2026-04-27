#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
from models.models import db, TestCase
from datetime import datetime, timezone
from werkzeug.exceptions import BadRequest
from services.case_service import CaseService
from flask import Blueprint, request, jsonify, current_app
from utils.utils_business_logic.case_id_generator import generate_case_id_from_data
from utils.utils_core.api_error_handler import build_internal_error_result
from config.settings import settings as config_settings
import re

# 创建蓝图
cases_bp = Blueprint('cases', __name__)

# 初始化服务
case_service = CaseService()


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
    except Exception:
        return False


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
        case_count = data.get('case_count', 5)
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
                # 使用新的ID生成服务生成唯一ID
                case_id = generate_case_id_from_data(case_data)

                test_case = TestCase(
                    case_id=case_id,  # 使用新的ID生成服务
                    title=case_data.get('title', ''),
                    description=case_data.get('description', ''),
                    precondition=case_data.get('precondition', case_data.get('preconditions', '')),
                    steps=json.dumps(case_data.get('steps', []), ensure_ascii=False),
                    expected_result=json.dumps(case_data.get('expected_result', case_data.get('expected', [])), ensure_ascii=False),
                    priority=case_data.get('priority', 'P2'),  # 使用AI返回的优先级，默认为P2
                    category=case_data.get('category', case_data.get('test_type', 'functional')),
                    test_method=case_data.get('test_method', ''),
                    module=case_data.get('module', ''),
                    tags=','.join(case_data.get('tags', [])),
                    status='draft',
                    created_by='system'
                )
                db.session.add(test_case)
                saved_cases.append(test_case.to_dict())

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'成功生成{len(saved_cases)}个测试用例',
                'cases': saved_cases,
                'total': len(saved_cases)
            })
        else:
            status_code = int(result.get('status_code') or 500)
            return jsonify({
                'success': False,
                'message': result.get('message', '生成用例失败'),
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
    """批量生成测试用例"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        requirements = data.get('requirements', [])
        if not requirements:
            raise BadRequest("需求列表不能为空")

        # 批量生成参数
        use_rag = _resolve_case_generation_use_rag()
        case_count_per_req = data.get('case_count_per_req', 3)
        process_mode = data.get('process_mode', 'sequential')
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
            # 保存所有生成的用例
            all_saved_cases = []
            for req_result in result['results']:
                if req_result['success']:
                    for case_data in req_result['cases']:
                        test_case = TestCase(
                            case_id=generate_case_id_from_data(case_data),
                            display_id=case_data.get('display_id', ''),
                            title=case_data.get('title', ''),
                            description=case_data.get('description', ''),
                            precondition=case_data.get('precondition', case_data.get('preconditions', '')),
                            steps=json.dumps(case_data.get('steps', []), ensure_ascii=False),
                            expected_result=json.dumps(case_data.get('expected_result', case_data.get('expected', [])), ensure_ascii=False),
                            priority=case_data.get('priority', 'P2'),  # 使用AI返回的优先级，默认为P2
                            category=case_data.get('category', case_data.get('test_type', 'functional')),
                            test_method=case_data.get('test_method', ''),
                            module=case_data.get('module', ''),
                            tags=','.join(case_data.get('tags', [])),
                            status='draft',
                            created_by='system',
                            requirement_id=req_result.get('requirement_id')
                        )
                        db.session.add(test_case)
                        all_saved_cases.append(test_case.to_dict())

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'批量生成完成，共生成{len(all_saved_cases)}个测试用例',
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


@cases_bp.route('/list', methods=['GET'])
def list_test_cases():
    """获取测试用例列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category')
        priority = request.args.get('priority')
        status = request.args.get('status')
        search = request.args.get('search', '').strip()

        # 构建查询
        query = TestCase.query

        # 添加筛选条件
        if category:
            query = query.filter(TestCase.category == category)
        if priority:
            query = query.filter(TestCase.priority == priority)
        if status:
            query = query.filter(TestCase.status == status)
        if search:
            query = query.filter(
                TestCase.title.contains(search) |
                TestCase.description.contains(search) |
                TestCase.case_id.contains(search)
            )

        # 排序和分页
        query = query.order_by(TestCase.created_time.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

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

        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        # 更新字段
        if 'title' in data:
            test_case.title = data['title']
        if 'description' in data:
            test_case.description = data['description']
        if 'precondition' in data:
            test_case.precondition = data['precondition']
        if 'steps' in data:
            test_case.steps = json.dumps(data['steps'], ensure_ascii=False)
        if 'expected_result' in data:
            test_case.expected_result = data['expected_result']
        if 'priority' in data:
            test_case.priority = data['priority']
        if 'category' in data:
            test_case.category = data['category']
        if 'tags' in data:
            test_case.tags = ','.join(data['tags']) if isinstance(data['tags'], list) else data['tags']
        if 'status' in data:
            test_case.status = data['status']

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
        # 总数统计
        total_cases = TestCase.query.count()

        # 按状态统计
        status_stats = db.session.query(
            TestCase.status,
            db.func.count(TestCase.id)
        ).group_by(TestCase.status).all()

        # 按优先级统计
        priority_stats = db.session.query(
            TestCase.priority,
            db.func.count(TestCase.id)
        ).group_by(TestCase.priority).all()

        # 按分类统计
        category_stats = db.session.query(
            TestCase.category,
            db.func.count(TestCase.id)
        ).group_by(TestCase.category).all()

        return jsonify({
            'success': True,
            'stats': {
                'total_cases': total_cases,
                'by_status': dict(status_stats),
                'by_priority': dict(priority_stats),
                'by_category': dict(category_stats)
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

        # 为每个需求生成测试用例
        all_cases = []
        for req in requirements:
            result = case_service.generate_cases(
                requirement_text=req.get('content', ''),
                use_rag=use_rag,
                case_count=3,  # 每个需求生成3个用例
                category='functional',
                output_language=output_language,
                llm=getattr(current_app, 'llm_case_generation', None),  # type: ignore 使用用例生成专用LLM
                vector_db=getattr(current_app, 'vector_db', None) if use_rag else None  # type: ignore
            )
            
            if result['success']:
                all_cases.extend(result['cases'])

        # 保存生成的用例
        saved_cases = []
        for case_data in all_cases:
            test_case = TestCase(
                case_id=generate_case_id_from_data(case_data),
                title=case_data.get('title', ''),
                description=case_data.get('description', ''),
                precondition=case_data.get('precondition', ''),
                steps=json.dumps(case_data.get('steps', []), ensure_ascii=False),
                expected_result=json.dumps(case_data.get('expected_result', []), ensure_ascii=False),
                priority=case_data.get('priority', 'P2'),
                category=case_data.get('category', 'functional'),
                test_method=case_data.get('test_method', ''),
                module=case_data.get('module', ''),
                tags=','.join(case_data.get('tags', [])),
                status='draft',
                created_by='system'
            )
            db.session.add(test_case)
            saved_cases.append(test_case.to_dict())

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功生成{len(saved_cases)}个测试用例',
            'cases': saved_cases,
            'total': len(saved_cases)
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