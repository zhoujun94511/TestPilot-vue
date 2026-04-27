#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from utils.utils_business_logic.requirements_analyze import analyze_requirement
from utils.utils_performance_monitoring.token_monitor import count_tokens, record_llm_call
from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor
# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from utils.utils_document_processing.parser import file_loader
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

from utils.utils_core.common_utils import generate_id
from utils.utils_core.api_error_handler import build_model_error_result
from utils.utils_core import error_codes as ec
from models.models import Requirement
from config.settings import settings




class DocumentService:
    """文档处理服务"""

    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.supported_formats = ['txt', 'csv', 'docx', 'pdf']

    @staticmethod
    def _normalize_priority(value: str = 'medium') -> str:
        """统一优先级口径为 P0-P3。"""
        key = str(value or '').strip().lower()
        mapping = {
            'p0': 'P0',
            'critical': 'P0',
            'high': 'P1',
            'p1': 'P1',
            'medium': 'P2',
            'normal': 'P2',
            'p2': 'P2',
            'low': 'P3',
            'p3': 'P3'
        }
        return mapping.get(key, 'P2')

    def analyze_document_file(
            self,
            file_path: str,
            analysis_type: str = 'requirements',
            llm=None
    ) -> Dict[str, Any]:
        """
        分析文档文件

        Args:
            file_path: 文件路径
            analysis_type: 分析类型 (requirements, test_points, etc.)
            llm: 语言模型实例

        Returns:
            分析结果
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': '文件不存在',
                    'error': ec.FILE_NOT_FOUND,
                    'error_code': ec.FILE_NOT_FOUND,
                    'status_code': 404,
                    'retryable': False
                }

            if not llm:
                return {
                    'success': False,
                    'message': 'LLM实例未初始化',
                    'error': ec.MODEL_NOT_INITIALIZED,
                    'error_code': ec.MODEL_NOT_INITIALIZED,
                    'status_code': 503,
                    'retryable': False
                }

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 加载文档内容
            try:
                texts, splits, metadata = file_loader(file_path)
                if not texts:
                    return {
                        'success': False,
                        'message': '文件内容为空或无法解析',
                        'error': 'empty_content'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'文件解析失败: {str(e)}',
                    'error': ec.FILE_PARSE_FAILED,
                    'error_code': ec.FILE_PARSE_FAILED,
                    'status_code': 400,
                    'retryable': False
                }

            # 合并文本内容
            full_content = "\n".join(texts)

            # 执行分析
            result = self._analyze_content(
                content=full_content,
                analysis_type=analysis_type,
                llm=llm,
                file_path=file_path
            )

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)
            result['analysis_time'] = elapsed_time
            result['file_path'] = file_path
            result['content_length'] = len(full_content)

            return result

        except Exception as e:
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='文档分析失败',
                include_raw_error=True
            )

    @staticmethod
    def list_requirements(
            page: int = 1,
            per_page: int = 20,
            req_type: Optional[str] = None,
            priority: Optional[str] = None,
            status: Optional[str] = None,
            source_file: str = '',
            search: str = ''
    ) -> Dict[str, Any]:
        """查询需求列表（筛选 + 分页）。"""
        try:
            query = Requirement.query

            if req_type:
                query = query.filter(Requirement.type == req_type)
            if priority:
                query = query.filter(Requirement.priority == priority)
            if status:
                query = query.filter(Requirement.status == status)
            if source_file:
                query = query.filter(Requirement.source_file.contains(source_file))
            if search:
                query = query.filter(
                    Requirement.title.contains(search) |
                    Requirement.content.contains(search) |
                    Requirement.req_id.contains(search)
                )

            query = query.order_by(Requirement.created_time.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            requirements = [req.to_dict() for req in pagination.items]

            return {
                'success': True,
                'requirements': requirements,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'total_pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
        except Exception as e:
            logger.error(f"查询需求列表失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': '获取需求列表失败',
                'error': str(e)
            }

    def analyze_document_content(
            self,
            content: str,
            analysis_type: str = 'requirements',
            llm=None
    ) -> Dict[str, Any]:
        """
        分析文档内容

        Args:
            content: 文档内容
            analysis_type: 分析类型
            llm: 语言模型实例

        Returns:
            分析结果
        """
        try:
            if not content.strip():
                return {
                    'success': False,
                    'message': '文档内容为空',
                    'error': ec.EMPTY_CONTENT,
                    'error_code': ec.EMPTY_CONTENT,
                    'status_code': 400,
                    'retryable': False
                }

            if not llm:
                return {
                    'success': False,
                    'message': 'LLM实例未初始化',
                    'error': ec.MODEL_NOT_INITIALIZED,
                    'error_code': ec.MODEL_NOT_INITIALIZED,
                    'status_code': 503,
                    'retryable': False
                }

            # 记录开始时间
            start_time = self.performance_monitor.start_timer()

            # 执行分析
            result = self._analyze_content(
                content=content,
                analysis_type=analysis_type,
                llm=llm,
                file_path=None  # 文本输入没有文件路径
            )

            # 记录性能指标
            elapsed_time = self.performance_monitor.end_timer(start_time)
            result['analysis_time'] = elapsed_time
            result['content_length'] = len(content)

            return result

        except Exception as e:
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='内容分析失败',
                include_raw_error=True
            )

    def _analyze_content(
            self,
            content: str,
            analysis_type: str,
            llm,
            file_path: str = None
    ) -> Dict[str, Any]:
        """内部分析方法"""
        try:
            # Token计数和记录
            estimated_tokens = count_tokens(content)
            record_llm_call(estimated_tokens, is_actual=True, input_text=content)

            if analysis_type == 'requirements':
                # 需求分析
                resp_reqs = analyze_requirement(llm, content)
                if not resp_reqs:
                    return {
                        'success': False,
                        'message': '需求分析失败，未返回结果',
                        'error': ec.MODEL_UNKNOWN_ERROR,
                        'error_code': ec.MODEL_UNKNOWN_ERROR,
                        'status_code': 502,
                        'retryable': False
                    }

                # 转换为标准格式
                requirements = []
                import time
                base_timestamp = int(time.time() * 1000)  # 毫秒时间戳
                
                for i, req in enumerate(resp_reqs):
                    if isinstance(req, dict):
                        # 使用需求标题生成ID，添加时间戳确保唯一性
                        title = req.get('title', f'需求{i + 1}')
                        unique_id = f"REQ_{generate_id(title)}_{base_timestamp + i:03d}"
                        requirements.append({
                            'req_id': unique_id,
                            'title': title,
                            'content': req.get('content', req.get('description', '')),
                            'type': req.get('type', 'functional'),
                            'priority': self._normalize_priority(req.get('priority', 'medium')),
                            'category': req.get('category', 'general')
                        })

                # 保存需求到数据库
                saved_requirements = []
                db = None
                try:
                    from models.models import Requirement, db
                    from pathlib import Path
                    
                    # 如果是文件路径，只保存文件名
                    source_filename = None
                    if file_path:
                        source_filename = Path(file_path).name
                    
                    for req in requirements:
                        # 检查是否已存在相同的req_id
                        existing = Requirement.query.filter_by(req_id=req['req_id']).first()
                        if existing:
                            logger.warning(f"需求ID {req['req_id']} 已存在，跳过保存")
                            continue
                            
                        requirement = Requirement(
                            req_id=req['req_id'],
                            title=req['title'],
                            content=req['content'],
                            type=req['type'],
                            priority=req['priority'],
                            status='active',
                            source_file=source_filename
                        )
                        db.session.add(requirement)
                        saved_requirements.append(req)
                    
                    db.session.commit()
                    logger.info(f"成功保存{len(saved_requirements)}个需求到数据库")
                except Exception as e:
                    logger.error(f"保存需求到数据库失败: {str(e)}")
                    if db is not None:
                        db.session.rollback()

                return {
                    'success': True,
                    'message': f'成功分析出{len(requirements)}个需求',
                    'analysis_type': analysis_type,
                    'requirements': requirements,
                    'saved_requirements': saved_requirements,
                    'raw_response': resp_reqs,
                    'tokens_used': estimated_tokens
                }

            elif analysis_type == 'test_points':
                # 测试点分析
                test_points = self._extract_test_points(content, llm)
                return {
                    'success': True,
                    'message': f'成功提取{len(test_points)}个测试点',
                    'analysis_type': analysis_type,
                    'test_points': test_points,
                    'tokens_used': estimated_tokens
                }

            elif analysis_type == 'business_rules':
                # 业务规则分析
                business_rules = self._extract_business_rules(content, llm)
                return {
                    'success': True,
                    'message': f'成功提取{len(business_rules)}个业务规则',
                    'analysis_type': analysis_type,
                    'business_rules': business_rules,
                    'tokens_used': estimated_tokens
                }

            elif analysis_type == 'comprehensive':
                # 综合分析：同时执行需求分析、测试点提取和业务规则提取
                logger.info(f"开始综合分析，内容长度: {len(content)}")
                
                # 并行执行三种分析
                requirements_result = None
                test_points = []
                business_rules = []
                
                try:
                    # 1. 需求分析
                    resp_reqs = analyze_requirement(llm, content)
                    if resp_reqs:
                        import time
                        base_timestamp = int(time.time() * 1000)
                        requirements_result = []
                        for i, req in enumerate(resp_reqs):
                            if isinstance(req, dict):
                                title = req.get('title', f'需求{i + 1}')
                                unique_id = f"REQ_{generate_id(title)}_{base_timestamp + i:03d}"
                                requirements_result.append({
                                    'req_id': unique_id,
                                    'title': title,
                                    'content': req.get('content', req.get('description', '')),
                                    'type': req.get('type', 'functional'),
                                    'priority': self._normalize_priority(req.get('priority', 'medium')),
                                    'category': req.get('category', 'general')
                                })
                except Exception as e:
                    logger.error(f"综合分析 - 需求分析失败: {e}", exc_info=True)
                
                try:
                    # 2. 测试点提取
                    test_points = self._extract_test_points(content, llm)
                except Exception as e:
                    logger.error(f"综合分析 - 测试点提取失败: {e}", exc_info=True)
                
                try:
                    # 3. 业务规则提取
                    business_rules = self._extract_business_rules(content, llm)
                except Exception as e:
                    logger.error(f"综合分析 - 业务规则提取失败: {e}", exc_info=True)
                
                # 合并所有结果
                total_items = len(requirements_result or []) + len(test_points) + len(business_rules)
                
                return {
                    'success': True,
                    'message': f'综合分析完成：需求 {len(requirements_result or [])} 个，测试点 {len(test_points)} 个，业务规则 {len(business_rules)} 个',
                    'analysis_type': analysis_type,
                    'requirements': requirements_result or [],
                    'test_points': test_points,
                    'business_rules': business_rules,
                    'summary': {
                        'requirements_count': len(requirements_result or []),
                        'test_points_count': len(test_points),
                        'business_rules_count': len(business_rules),
                        'total_count': total_items
                    },
                    'tokens_used': estimated_tokens
                }

            else:
                return {
                    'success': False,
                    'message': f'不支持的分析类型: {analysis_type}',
                    'error': ec.VALIDATION_FAILED,
                    'error_code': ec.VALIDATION_FAILED,
                    'status_code': 400,
                    'retryable': False
                }

        except Exception as e:
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='分析处理失败',
                include_raw_error=True
            )

    @staticmethod
    def _extract_test_points(content: str, llm) -> List[Dict[str, Any]]:
        """提取测试点"""
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import JsonOutputParser
            import json
            import re
            
            zh_count = len(re.findall(r'[\u4e00-\u9fff]', content or ''))
            en_count = len(re.findall(r'[A-Za-z]', content or ''))
            if zh_count > en_count:
                language_instruction = "请使用简体中文填写测试点内容字段。"
            elif en_count > zh_count:
                language_instruction = "Please fill test point content fields in English."
            else:
                language_instruction = "请跟随文档主体语言输出测试点内容。"

            # 使用统一配置中的提示词模板
            prompt_template = settings.TEST_POINTS_PROMPT
            
            prompt = PromptTemplate.from_template(prompt_template)
            formatted_prompt = prompt.format(content=content, language_instruction=language_instruction)
            
            response = llm.invoke(formatted_prompt)
            
            # 获取响应内容
            if hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)
            
            # 尝试解析 JSON
            test_points = []
            try:
                # 尝试直接解析 JSON
                parsed_json = json.loads(response_content)
                if isinstance(parsed_json, dict) and 'test_points' in parsed_json:
                    test_points = parsed_json['test_points']
                elif isinstance(parsed_json, list):
                    test_points = parsed_json
                else:
                    logger.warning(f"JSON格式不符合预期: {type(parsed_json)}")
            except json.JSONDecodeError:
                # JSON 解析失败，尝试提取 JSON 部分
                json_match = re.search(r'\{.*"test_points".*}', response_content, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\[.*]', response_content, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        parsed_json = json.loads(json_str)
                        if isinstance(parsed_json, dict) and 'test_points' in parsed_json:
                            test_points = parsed_json['test_points']
                        elif isinstance(parsed_json, list):
                            test_points = parsed_json
                    except json.JSONDecodeError as json_err:
                        logger.error(f"提取的JSON解析也失败: {str(json_err)}")
                        logger.error(f"提取的JSON内容: {json_str[:500]}")
            
            # 标准化测试点数据
            standardized_points = []
            for i, point in enumerate(test_points):
                if isinstance(point, dict):
                    standardized_points.append({
                        'id': f"TP_{generate_id(point.get('name', f'test_point_{i}'))}_{i + 1:03d}",
                        'name': point.get('name', f'测试点{i + 1}'),
                        'description': point.get('description', point.get('description', '')),
                        'type': point.get('type', 'functional'),
                        'priority': DocumentService._normalize_priority(point.get('priority', 'medium'))
                    })
            
            return standardized_points[:20]  # 限制返回数量

        except Exception as e:
            logger.error(f"测试点提取失败: {e}", exc_info=True)
            return []

    @staticmethod
    def _extract_business_rules(content: str, llm) -> List[Dict[str, Any]]:
        """提取业务规则"""
        try:
            from langchain_core.prompts import PromptTemplate
            import json
            import re
            
            zh_count = len(re.findall(r'[\u4e00-\u9fff]', content or ''))
            en_count = len(re.findall(r'[A-Za-z]', content or ''))
            if zh_count > en_count:
                language_instruction = "请使用简体中文填写业务规则内容字段。"
            elif en_count > zh_count:
                language_instruction = "Please fill business rule content fields in English."
            else:
                language_instruction = "请跟随文档主体语言输出业务规则内容。"

            # 使用统一配置中的提示词模板
            prompt_template = settings.BUSINESS_RULES_PROMPT
            
            prompt = PromptTemplate.from_template(prompt_template)
            formatted_prompt = prompt.format(content=content, language_instruction=language_instruction)
            
            response = llm.invoke(formatted_prompt)
            
            # 获取响应内容
            if hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)
            
            # 尝试解析 JSON
            business_rules = []
            try:
                # 尝试直接解析 JSON
                parsed_json = json.loads(response_content)
                if isinstance(parsed_json, dict) and 'business_rules' in parsed_json:
                    business_rules = parsed_json['business_rules']
                elif isinstance(parsed_json, list):
                    business_rules = parsed_json
                else:
                    logger.warning(f"JSON格式不符合预期: {type(parsed_json)}")
            except json.JSONDecodeError:
                # JSON 解析失败，尝试提取 JSON 部分
                json_match = re.search(r'\{.*"business_rules".*}', response_content, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\[.*]', response_content, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        parsed_json = json.loads(json_str)
                        if isinstance(parsed_json, dict) and 'business_rules' in parsed_json:
                            business_rules = parsed_json['business_rules']
                        elif isinstance(parsed_json, list):
                            business_rules = parsed_json
                    except json.JSONDecodeError as json_err:
                        logger.error(f"提取的JSON解析也失败: {str(json_err)}")
                        logger.error(f"提取的JSON内容: {json_str[:500]}")
            
            # 标准化业务规则数据
            standardized_rules = []
            for i, rule in enumerate(business_rules):
                if isinstance(rule, dict):
                    standardized_rules.append({
                        'id': f"BR_{generate_id(rule.get('name', f'business_rule_{i}'))}_{i + 1:03d}",
                        'name': rule.get('name', f'业务规则{i + 1}'),
                        'description': rule.get('description', rule.get('description', '')),
                        'type': rule.get('type', 'validation'),
                        'condition': rule.get('condition', rule.get('condition', ''))
                    })
            
            return standardized_rules[:15]  # 限制返回数量

        except Exception as e:
            logger.error(f"业务规则提取失败: {e}", exc_info=True)
            return []

    def validate_document_format(self, file_path: str) -> Dict[str, Any]:
        """
        验证文档格式

        Args:
            file_path: 文件路径

        Returns:
            验证结果
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'message': '文件不存在',
                    'error': 'file_not_found'
                }

            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            if file_ext not in self.supported_formats:
                return {
                    'valid': False,
                    'message': f'不支持的文件格式: {file_ext}',
                    'supported_formats': self.supported_formats
                }

            # 检查文件大小
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                return {
                    'valid': False,
                    'message': f'文件过大: {file_size} bytes，最大支持: {max_size} bytes'
                }

            # 尝试读取文件内容
            try:
                texts, _, _ = file_loader(file_path)
                content_length = len('\n'.join(texts)) if texts else 0

                return {
                    'valid': True,
                    'message': '文档格式有效',
                    'file_info': {
                        'format': file_ext,
                        'size': file_size,
                        'content_length': content_length
                    }
                }

            except Exception as e:
                return {
                    'valid': False,
                    'message': f'文件内容读取失败: {str(e)}',
                    'error': 'content_read_failed'
                }

        except Exception as e:
            return {
                'valid': False,
                'message': f'文档验证失败: {str(e)}',
                'error': str(e)
            }

    @staticmethod
    def get_document_summary(content: str, llm=None) -> Dict[str, Any]:
        """
        获取文档摘要

        Args:
            content: 文档内容
            llm: 语言模型实例

        Returns:
            文档摘要
        """
        try:
            if not llm:
                return {
                    'success': False,
                    'message': 'LLM实例未初始化'
                }

            # 如果内容太长，截取前部分
            max_length = 4000
            if len(content) > max_length:
                content = content[:max_length] + "..."

            prompt = f"""
            请为以下文档生成一个简洁的摘要，包括：
            1. 文档主要内容
            2. 关键信息点
            3. 文档类型和用途

            文档内容：
            {content}

            请用中文回答，控制在200字以内。
            """

            response = llm.invoke(prompt)
            summary = response.content if hasattr(response, 'content') else str(response)

            return {
                'success': True,
                'summary': summary.strip(),
                'content_length': len(content),
                'summary_length': len(summary)
            }

        except Exception as e:
            return build_model_error_result(
                getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'),
                e,
                fallback_message='摘要生成失败',
                include_raw_error=True
            )