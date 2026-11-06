#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from models.models import db, Requirement
from werkzeug.exceptions import BadRequest
from services.document_service import DocumentService
from services.document_meta import (
    document_matches_analysis_filter,
    is_document_meta_file,
    normalize_analysis_type,
    persist_document_analysis_type,
    read_document_meta,
    resolve_stored_analysis_type,
    stamp_document_ownership,
    write_document_meta,
)
from utils.utils_core.upload_storage import build_versioned_storage_filename, resolve_display_filename
from flask import Blueprint, request, jsonify, current_app
from utils.utils_core.api_response import api_success, api_error
from utils.utils_core.api_error_handler import build_internal_error_result
from services.data_scope import can_access_document_filename, can_access_record
from services.document_service import delete_requirements
from services.document_meta import meta_path_for_document
from services.sql_query_helpers import filter_by_eq, path_name_matches
from services.stats_scope import scoped_requirements_query

# 创建蓝图
documents_bp = Blueprint('documents', __name__)

# 与 DocumentService.validate_document 的上限一致
MAX_DOCUMENT_UPLOAD_BYTES = 50 * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 1024 * 1024


def _file_too_large_response():
    return jsonify({
        'success': False,
        'message': f'文件过大，最大支持 {MAX_DOCUMENT_UPLOAD_BYTES // (1024 * 1024)}MB',
        'error_code': 'FILE_TOO_LARGE',
    }), 413

# 初始化服务
document_service = DocumentService()


def _document_success(data=None, code='DOCUMENT_SUCCESS', message_key='documents.message.success', message='Document operation completed successfully', **extra):
    return api_success(data=data, code=code, message_key=message_key, message=message, **extra)


def _document_error(code, message_key, message, status=400, message_params=None, details=None, **extra):
    return api_error(
        code=code,
        message_key=message_key,
        message=message,
        status=status,
        message_params=message_params,
        details=details,
        **extra
    )


def _document_file(name):
    """按文件名定位 uploads/documents 下的文档；带目录、指向说明文件或越界的都视为不存在。"""
    safe_name = Path(str(name or '')).name
    if not safe_name or safe_name in {'.', '..'} or safe_name != str(name or '').strip():
        return None
    documents_dir = (Path(current_app.config['UPLOAD_FOLDER']) / 'documents').resolve()
    full_path = (documents_dir / safe_name).resolve()
    if full_path.parent != documents_dir or not full_path.is_file() or is_document_meta_file(full_path):
        return None
    return full_path


def _requirements_of_document(filename):
    """文档按部门共用。删文件时清掉本部门各项目里来自这份文件的需求，不只清当前项目。"""
    from services.data_scope import apply_data_scope

    return apply_data_scope(
        Requirement.query, Requirement, 'requirements', project=False
    ).filter(path_name_matches(Requirement.source_file, filename))


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    """上传文档"""
    # 必须在读取 request.files 之前判断，否则 werkzeug 会先把整个请求体写进临时文件
    body_limit = MAX_DOCUMENT_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
    if (request.content_length or 0) > body_limit:
        return _file_too_large_response()
    request.max_content_length = body_limit
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400

        # 检查文件类型
        allowed_extensions = {'.txt', '.md', '.csv', '.docx', '.json', '.xlsx', '.pdf', '.yaml', '.yml'}
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400

        # 落盘前校验大小，避免超大文件先占满磁盘
        file.stream.seek(0, os.SEEK_END)
        upload_size = file.stream.tell()
        file.stream.seek(0)
        if upload_size > MAX_DOCUMENT_UPLOAD_BYTES:
            return _file_too_large_response()

        # 保存文件
        upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / 'documents'
        upload_dir.mkdir(parents=True, exist_ok=True)

        stored_filename, original_filename = build_versioned_storage_filename(file.filename)
        file_path = upload_dir / stored_filename
        file.save(str(file_path))

        upload_analysis_type = normalize_analysis_type(request.form.get('analysis_type', 'requirements'))
        write_document_meta(
            file_path,
            {
                'original_filename': original_filename,
                'analysis_type': upload_analysis_type,
                'analysis_status': 'uploaded',
                'uploaded_at': datetime.now(timezone.utc).isoformat()
            }
        )
        stamp_document_ownership(file_path)

        # 返回文件信息
        # 确保返回正确的相对路径格式
        relative_path = file_path.relative_to(Path(current_app.config['UPLOAD_FOLDER']))
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'data': {
                'filename': stored_filename,
                'original_filename': original_filename,
                'display_name': original_filename,
                'file_path': relative_path.as_posix(),  # 使用pathlib的as_posix()方法统一返回正斜杠格式，跨平台兼容
                'size': file_path.stat().st_size
            }
        })

    except Exception as e:
        current_app.logger.error(f"文件上传失败: {e}")
        return jsonify({
            'success': False,
            'message': '文件上传失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/analyze', methods=['POST'])
def analyze_document():
    """分析文档内容"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("请求数据不能为空")

        # 获取分析参数
        file_path = data.get('file_path')
        content = data.get('content')
        analysis_type = data.get('analysis_type', 'requirements')  # requirements, test_points, etc.

        if not file_path and not content:
            raise BadRequest("必须提供文件路径或文本内容")

        # 执行文档分析
        if file_path:
            # 从文件分析
            upload_root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
            full_path = (upload_root / str(file_path)).resolve()
            if full_path.parent != (upload_root / 'documents'):
                raise BadRequest("文件路径无效")
            full_path = _document_file(full_path.name)
            if full_path is None:
                raise BadRequest(f"文件不存在: {Path(str(file_path)).name}")
            doc_name = full_path.name
            if not can_access_document_filename(doc_name):
                return jsonify({
                    'success': False,
                    'message': '无权分析该文档',
                }), 403

            result = document_service.analyze_document_file(
                file_path=str(full_path),
                analysis_type=analysis_type,
                llm=getattr(current_app, 'llm_requirement_analysis', None)  # type: ignore 使用需求分析专用LLM
            )
        else:
            # 从文本内容分析
            result = document_service.analyze_document_content(
                content=content,
                analysis_type=analysis_type,
                llm=getattr(current_app, 'llm_requirement_analysis', None)  # type: ignore 使用需求分析专用LLM
            )

        if result['success']:
            return jsonify({
                'success': True,
                'message': '文档分析成功',
                'data': result
            })
        else:
            status_code = int(result.get('status_code') or 500)
            return jsonify({
                'success': False,
                'message': result.get('message', '文档分析失败'),
                'error': result.get('error', 'unknown_error'),
                'error_code': result.get('error_code'),
                'retryable': bool(result.get('retryable', False))
            }), status_code

    except BadRequest as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"文档分析失败: {e}")
        error_payload = build_internal_error_result(message='文档分析失败')
        return jsonify({
            'success': False,
            'message': error_payload['message'],
            'error': error_payload['error'],
            'error_code': error_payload['error_code'],
            'retryable': error_payload['retryable']
        }), error_payload['status_code']


@documents_bp.route('/list', methods=['GET'])
def list_documents():
    """获取已上传文档列表"""
    try:
        # 获取分页参数
        page = max(1, request.args.get('page', 1, type=int) or 1)
        per_page = min(max(1, request.args.get('per_page', 10, type=int) or 10), 100)
        search = request.args.get('search', '').strip()
        analysis_type = request.args.get('analysis_type', '').strip().lower()

        # 修复路径拼接问题
        upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / 'documents'
        if not upload_dir.exists():
            return jsonify({
                'success': True,
                'documents': [],
                'total': 0,
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0
                }
            })

        scoped_req = scoped_requirements_query()
        documents = []
        for file_path in upload_dir.iterdir():
            if not file_path.is_file() or is_document_meta_file(file_path):
                continue
            stat = file_path.stat()
            filename = file_path.name
            if not can_access_document_filename(filename):
                continue
            stored_analysis_type = resolve_stored_analysis_type(file_path)
            if hasattr(Requirement, 'source_file'):
                by_file = scoped_req.filter(path_name_matches(Requirement.source_file, filename))
                requirements_count = by_file.count()
                functional_count = filter_by_eq(by_file, Requirement.type, 'functional').count()
                business_count = filter_by_eq(by_file, Requirement.type, 'business').count()
            else:
                requirements_count = 0
                functional_count = 0
                business_count = 0

            # 历史文件无 meta：已分析过的视为「综合分析」，避免按需求条数误出现在各专项筛选里
            if stored_analysis_type is None and requirements_count > 0:
                stored_analysis_type = 'comprehensive'

            meta = read_document_meta(file_path)
            display_name = resolve_display_filename(filename, meta)
            documents.append({
                'id': file_path.stem,
                'filename': filename,
                'original_filename': meta.get('original_filename') or display_name,
                'display_name': display_name,
                'file_size': stat.st_size,
                'file_type': file_path.suffix[1:] if file_path.suffix else '',
                'created_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'relative_path': filename,
                'requirements_count': requirements_count,
                'functional_count': functional_count,
                'business_count': business_count,
                'analysis_type': stored_analysis_type,
            })

        # 应用搜索过滤（文件名 + 关联需求标题/内容/编号）
        if search:
            search_lower = search.lower()
            search_escaped = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            matched = []
            for doc in documents:
                filename = doc['filename']
                if search_lower in filename.lower():
                    matched.append(doc)
                    continue
                if hasattr(Requirement, 'source_file'):
                    search_clause = cast(
                        ColumnElement[bool],
                        or_(
                            Requirement.title.ilike(f'%{search_escaped}%', escape='\\'),
                            Requirement.content.ilike(f'%{search_escaped}%', escape='\\'),
                            Requirement.req_id.ilike(f'%{search_escaped}%', escape='\\'),
                        ),
                    )
                    has_req = scoped_req.filter(
                        path_name_matches(Requirement.source_file, filename)
                    ).filter(search_clause).limit(1).count()
                    if has_req:
                        matched.append(doc)
            documents = matched

        # 按上传/分析时保存的 analysis_type 过滤（勿用需求条数，综合分析会误命中各类型）
        if analysis_type:
            documents = [
                doc
                for doc in documents
                if document_matches_analysis_filter(doc.get('analysis_type'), analysis_type)
            ]

        # 按上传时间倒序排序
        documents.sort(key=lambda x: x['created_time'], reverse=True)

        # 计算分页
        total_documents = len(documents)
        total_pages = (total_documents + per_page - 1) // per_page if total_documents > 0 else 0
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_documents = documents[start_idx:end_idx]

        return jsonify({
            'success': True,
            'documents': paginated_documents,
            'total': total_documents,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_documents,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
        })

    except Exception as e:
        current_app.logger.error(f"获取文档列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取文档列表失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/<path:file_path>', methods=['DELETE'])
def delete_document(file_path):
    """删除文档"""
    try:
        # 只接受文件名，避免 documents/ 前缀被再拼一次
        safe_name = Path(str(file_path or '')).name
        full_path = _document_file(safe_name)
        if full_path is None:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        if not can_access_document_filename(safe_name):
            return jsonify({
                'success': False,
                'message': '无权删除该文档',
            }), 403

        # 先在事务里删需求，文件删掉后再提交；文件删不掉就回滚，两边保持一致
        delete_requirements(_requirements_of_document(safe_name))
        try:
            full_path.unlink()
        except OSError as exc:
            db.session.rollback()
            current_app.logger.error("删除文档文件失败，需求记录已保留: %s", exc)
            return jsonify({
                'success': False,
                'message': '文件删除失败，需求记录已保留',
                'error': 'FILE_DELETE_FAILED',
                'error_code': 'FILE_DELETE_FAILED',
                'retryable': True
            }), 500
        db.session.commit()
        try:
            meta_path_for_document(full_path).unlink(missing_ok=True)
        except OSError as exc:
            current_app.logger.warning("文档说明文件删除失败: %s", exc)

        return jsonify({
            'success': True,
            'message': '文档删除成功'
        })

    except BadRequest as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'bad_request'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除文档失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除文档失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/requirements', methods=['GET'])
def list_requirements():
    """获取需求列表"""
    try:
        # 获取查询参数
        page = max(1, request.args.get('page', 1, type=int) or 1)
        per_page = min(max(1, request.args.get('per_page', 20, type=int) or 20), 1000)
        req_type = request.args.get('type')
        priority = request.args.get('priority')
        status = request.args.get('status')
        source_file = request.args.get('source_file', '').strip()
        search = request.args.get('search', '').strip()

        result = document_service.list_requirements(
            page=page,
            per_page=per_page,
            req_type=req_type,
            priority=priority,
            status=status,
            source_file=source_file,
            search=search,
            exact_source=request.args.get('exact_source', '').strip().lower() in ('1', 'true')
        )
        if not result.get('success'):
            return jsonify({
                'success': False,
                'message': result.get('message', '获取需求列表失败'),
                'error': result.get('error')
            }), 500

        return jsonify({
            'success': True,
            'requirements': result.get('requirements', []),
            'page': page,
            'per_page': per_page,
            'total': result['pagination']['total'],
            'total_pages': result['pagination']['total_pages'],
            'has_prev': result['pagination']['has_prev'],
            'has_next': result['pagination']['has_next'],
            'pagination': result['pagination']
        })

    except Exception as e:
        current_app.logger.error(f"获取需求列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取需求列表失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/requirements/<string:req_id>', methods=['GET'])
def get_requirement(req_id):
    """获取单个需求详情"""
    try:
        requirement = Requirement.query.filter_by(req_id=req_id).first()
        if not requirement:
            return jsonify({
                'success': False,
                'message': '需求不存在'
            }), 404
        if not can_access_record(requirement, 'requirements'):
            return jsonify({
                'success': False,
                'message': '没有权限访问该需求',
                'message_key': 'common.errors.http403',
            }), 403

        return jsonify({
            'success': True,
            'requirement': requirement.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"获取需求详情失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取需求详情失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/requirements/<string:req_id>', methods=['PUT'])
def update_requirement(req_id):
    """更新需求"""
    try:
        requirement = Requirement.query.filter_by(req_id=req_id).first()
        if not requirement:
            return jsonify({
                'success': False,
                'message': '需求不存在'
            }), 404
        if not can_access_record(requirement, 'requirements'):
            return jsonify({
                'success': False,
                'message': '没有权限修改该需求',
                'message_key': 'common.errors.http403',
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400

        from services.record_conflict import MissingRevision, RecordConflict, ensure_unchanged

        try:
            ensure_unchanged(requirement, data.get('updated_time'))
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
            requirement.title = data['title']
        if 'content' in data:
            requirement.content = data['content']
        if 'type' in data:
            requirement.type = data['type']
        if 'priority' in data:
            from services.case_field_filters import normalize_priority

            requirement.priority = normalize_priority(data['priority'])
        if 'status' in data:
            requirement.status = data['status']

        requirement.updated_time = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '需求更新成功',
            'requirement': requirement.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"更新需求失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '更新需求失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/requirements/<string:req_id>', methods=['DELETE'])
def delete_requirement(req_id):
    """删除需求"""
    try:
        requirement = Requirement.query.filter_by(req_id=req_id).first()
        if not requirement:
            return jsonify({
                'success': False,
                'message': '需求不存在'
            }), 404
        if not can_access_record(requirement, 'requirements'):
            return jsonify({
                'success': False,
                'message': '没有权限删除该需求',
                'message_key': 'common.errors.http403',
            }), 403

        delete_requirements(Requirement.query.filter(Requirement.id == requirement.id))
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '需求删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除需求失败: {e}")
        return jsonify({
            'success': False,
            'message': '删除需求失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/<string:document_id>/preview', methods=['GET'])
def get_document_preview(document_id):
    """获取文档预览"""
    try:
        file_path = _document_file(document_id)
        if file_path is None:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        if not can_access_document_filename(document_id):
            return jsonify({
                'success': False,
                'message': '无权预览该文档',
            }), 403
        
        # 使用通用预览工具，支持多种文件格式
        from utils.utils_document_processing.file_preview import get_file_preview
        
        file_size = file_path.stat().st_size
        preview_result = get_file_preview(str(file_path), max_length=1024 * 1024, max_csv_rows=100)
        
        return jsonify({
            'success': True,
            'preview': {
                'content': preview_result.get('content', '无法预览'),
                'content_type': preview_result.get('content_type', 'text'),  # text, html, json
                'filename': file_path.name,
                'file_size': file_size,
                'file_type': preview_result.get('file_type', file_path.suffix[1:] if file_path.suffix else 'unknown'),
                'is_truncated': preview_result.get('is_truncated', False)
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取文档预览失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取文档预览失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500


@documents_bp.route('/<string:document_id>/reanalyze', methods=['POST'])
def reanalyze_document(document_id):
    """重新分析文档"""
    try:
        file_path = _document_file(document_id)
        if file_path is None:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        if not can_access_document_filename(document_id):
            return jsonify({
                'success': False,
                'message': '无权重新分析该文档',
            }), 403
        
        # 获取分析类型（默认为需求分析）
        data = request.get_json() or {}
        analysis_type = data.get('analysis_type', 'requirements')
        
        # 执行文档分析
        result = document_service.analyze_document_file(
            file_path=str(file_path),
            analysis_type=analysis_type,
            llm=getattr(current_app, 'llm_requirement_analysis', None)  # type: ignore 使用需求分析专用LLM
        )
        
        if result['success']:
            persist_document_analysis_type(file_path, analysis_type)
            return jsonify({
                'success': True,
                'message': '文档重新分析完成',
                'data': result
            })
        else:
            status_code = int(result.get('status_code') or 500)
            return jsonify({
                'success': False,
                'message': result.get('message', '文档分析失败'),
                'error': result.get('error'),
                'error_code': result.get('error_code'),
                'retryable': bool(result.get('retryable', False))
            }), status_code
            
    except Exception as e:
        current_app.logger.error(f"重新分析文档失败: {e}")
        return jsonify({
            'success': False,
            'message': '重新分析文档失败',
            'error': 'INTERNAL_SERVER_ERROR',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'retryable': False
        }), 500
