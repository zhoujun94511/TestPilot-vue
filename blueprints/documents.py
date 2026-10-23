#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from models.models import db, Requirement
from werkzeug.exceptions import BadRequest
from services.document_service import DocumentService
from flask import Blueprint, request, jsonify, current_app
from utils.utils_core.api_response import api_success, api_error
from utils.utils_core.api_error_handler import build_internal_error_result

# 创建蓝图
documents_bp = Blueprint('documents', __name__)

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


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    """上传文档"""
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

        # 保存文件
        upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / 'documents'
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 处理文件名，支持中文字符
        def safe_filename(input_filename):
            """创建安全的文件名，保留中文字符"""
            import re
            import unicodedata
            
            # 分离文件名和扩展名
            file_name, file_ext = os.path.splitext(input_filename)
            
            # 对文件名部分进行安全处理
            # 保留中文字符、英文字母、数字、连字符、下划线
            safe_name = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', file_name)
            
            # 移除连续的下划线
            safe_name = re.sub(r'_+', '_', safe_name)
            
            # 移除开头和结尾的下划线
            safe_name = safe_name.strip('_')
            
            # 如果处理后的文件名为空，使用默认名称
            if not safe_name:
                safe_name = 'document'
            
            return safe_name + file_ext
        
        filename = safe_filename(file.filename)
        file_path = upload_dir / filename

        # 如果文件已存在，添加时间戳
        if file_path.exists():
            file_name_part, file_ext_part = os.path.splitext(filename)
            timestamp = int(time.time())
            filename = f"{file_name_part}_{timestamp}{file_ext_part}"
            file_path = upload_dir / filename

        file.save(str(file_path))

        # 返回文件信息
        # 确保返回正确的相对路径格式
        relative_path = file_path.relative_to(Path(current_app.config['UPLOAD_FOLDER']))
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'data': {
                'filename': filename,
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
            # 使用pathlib自动处理路径格式，跨平台兼容
            full_path = Path(current_app.config['UPLOAD_FOLDER']) / file_path
            if not full_path.exists():
                raise BadRequest(f"文件不存在: {full_path}")

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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()
        
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

        documents = []
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                # 统计与该文档相关的需求数量和分类
                filename = file_path.name
                if hasattr(Requirement, 'source_file'):
                    # 总需求数量
                    requirements_count = Requirement.query.filter(
                        Requirement.source_file.like(f'%{filename}%')
                    ).count()
                    
                    # 功能需求数量
                    functional_count = Requirement.query.filter(
                        Requirement.source_file.like(f'%{filename}%'),
                        Requirement.type == 'functional'
                    ).count()
                    
                    # 业务需求数量
                    business_count = Requirement.query.filter(
                        Requirement.source_file.like(f'%{filename}%'),
                        Requirement.type == 'business'
                    ).count()
                else:
                    requirements_count = 0
                    functional_count = 0
                    business_count = 0
                
                documents.append({
                    'id': file_path.stem,  # 使用文件名（不含扩展名）作为ID
                    'filename': filename,
                    'file_size': stat.st_size,
                    'file_type': file_path.suffix[1:] if file_path.suffix else '',
                    'created_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'relative_path': filename,  # 只返回文件名，不包含documents/前缀
                    'requirements_count': requirements_count,
                    'functional_count': functional_count,  # 功能需求数量
                    'business_count': business_count  # 业务需求数量
                })

        # 应用搜索过滤
        if search:
            documents = [doc for doc in documents if search.lower() in doc['filename'].lower()]
        
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
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        safe_name = Path(str(file_path or '')).name
        if not safe_name or safe_name in {'.', '..'}:
            raise BadRequest("非法的文件路径")
        full_path = upload_folder / 'documents' / safe_name
        if not full_path.exists():
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        # 检查文件路径安全性
        if not str(full_path.resolve()).startswith(str((upload_folder / 'documents').resolve())):
            raise BadRequest("非法的文件路径")

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

        try:
            Requirement.query.filter_by(source_file=safe_name).delete(synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.error("文档文件已删除，但需求记录提交失败: %s", safe_name)
            raise

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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
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
            search=search
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

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400

        # 更新字段
        if 'title' in data:
            requirement.title = data['title']
        if 'content' in data:
            requirement.content = data['content']
        if 'type' in data:
            requirement.type = data['type']
        if 'priority' in data:
            requirement.priority = data['priority']
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

        db.session.delete(requirement)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '需求删除成功'
        })

    except Exception as e:
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
        # document_id是文件名
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        file_path = upload_folder / 'documents' / document_id
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        # 检查文件路径安全性
        if not str(file_path.resolve()).startswith(str(upload_folder.resolve())):
            raise BadRequest("非法的文件路径")
        
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
        # document_id是文件名
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        file_path = upload_folder / 'documents' / document_id
        
        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        # 检查文件路径安全性
        if not str(file_path.resolve()).startswith(str(upload_folder.resolve())):
            raise BadRequest("非法的文件路径")
        
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
