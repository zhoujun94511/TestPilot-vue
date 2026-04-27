#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
API配置服务模块
专门处理前端API所需的配置数据
职责：为前端提供配置选项，不处理业务逻辑配置
"""
import os
from typing import Dict, List, Any
from config.settings import settings
from services.config_center_service import config_center_service


class ConfigService:
    """
    API配置服务类
    
    职责：
    - 为前端API提供配置选项
    - 处理用例生成相关的配置
    - 不处理系统性能优化配置
    """
    
    def __init__(self):
        pass
    
    def get_case_generation_config(self) -> Dict[str, Any]:
        """
        获取用例生成配置选项
        
        Returns:
            配置字典
        """
        try:
            # 获取最大生成数量
            max_case_num = getattr(settings, 'MAX_CASE_NUM', 50)
            
            # 生成数量选项
            case_count_options = self._get_case_count_options(max_case_num)
            
            # 测试类型选项
            test_type_options = self._get_test_type_options()
            enable_case_generation_rag = self._resolve_case_generation_rag_enabled()
            
            return {
                'case_count_options': case_count_options,
                'test_type_options': test_type_options,
                'max_case_num': max_case_num,
                'default_case_count': min(5, max_case_num),
                'priority_auto_determined': True,  # 优先级由AI自动判断
                'enable_case_generation_rag': enable_case_generation_rag
            }
            
        except Exception as e:
            raise Exception(f"获取用例生成配置失败: {e}")

    @staticmethod
    def _resolve_case_generation_rag_enabled() -> bool:
        if not getattr(settings, 'ENABLE_VECTOR_STORE', True):
            return False
        value = config_center_service.get_config_value('ENABLE_CASE_GENERATION_RAG', False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def _get_case_count_options(max_case_num: int) -> List[Dict[str, Any]]:
        """
        获取用例生成数量选项
        
        Args:
            max_case_num: 最大生成数量
            
        Returns:
            选项列表
        """
        case_count_options = []
        
        # 从环境变量获取常用选项
        common_options_str = os.getenv('CASE_COUNT_OPTIONS', '1,2,3,5,8,10,15,20,25,30')
        try:
            common_options = [int(x.strip()) for x in common_options_str.split(',') if x.strip()]
        except ValueError:
            # 如果解析失败，使用默认值
            common_options = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30]
        
        # 添加常用选项（不超过最大限制）
        for option in common_options:
            if option <= max_case_num:
                case_count_options.append({
                    'value': option,
                    'label': f'{option}个'
                })
        
        # 如果最大数量不在常用选项中，添加最大数量选项
        if max_case_num not in common_options:
            case_count_options.append({
                'value': max_case_num,
                'label': f'{max_case_num}个（最大）'
            })
        
        return case_count_options
    
    @staticmethod
    def _get_test_type_options() -> List[Dict[str, str]]:
        """
        获取测试类型选项
        
        Returns:
            测试类型选项列表
        """
        return [
            {'value': 'functional', 'label': '功能测试'},
            {'value': 'performance', 'label': '性能测试'},
            {'value': 'security', 'label': '安全测试'},
            {'value': 'compatibility', 'label': '兼容性测试'},
            {'value': 'usability', 'label': '易用性测试'},
            {'value': 'integration', 'label': '集成测试'},
            {'value': 'regression', 'label': '回归测试'}
        ]
    
    @staticmethod
    def get_system_config() -> Dict[str, Any]:
        """
        获取系统配置信息
        
        Returns:
            系统配置字典
        """
        try:
            return {
                'max_case_num': getattr(settings, 'MAX_CASE_NUM', 50),
                'enable_parallel': getattr(settings, 'ENABLE_PARALLEL', True),
                'enable_streaming': getattr(settings, 'ENABLE_STREAMING', False),
                'content_similarity_threshold': getattr(settings, 'CONTENT_SIMILARITY_THRESHOLD', 0.8),
                'enable_content_dedup': getattr(settings, 'ENABLE_CONTENT_DEDUP', True),
                'rag_top_k': getattr(settings, 'RAG_TOP_K', 5),
                'rag_score_threshold': getattr(settings, 'RAG_SCORE_THRESHOLD', 0.7)
            }
        except Exception as e:
            raise Exception(f"获取系统配置失败: {e}")
