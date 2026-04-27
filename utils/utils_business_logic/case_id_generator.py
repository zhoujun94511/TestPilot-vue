"""
测试用例ID生成服务
使用时间戳 + 模块 + 序列号的策略生成唯一且可读的测试用例ID
"""
import threading
from datetime import datetime
from typing import Dict, Optional
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)

class CaseIdGenerator:
    """测试用例ID生成器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CaseIdGenerator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            # 存储每个模块的序列号计数器
            self._counters: Dict[str, int] = {}
            self._instance_lock = threading.Lock()
            self._initialized = True
    
    def generate_case_id(self, module: str = "DEFAULT", prefix: str = "TC") -> str:
        """
        生成唯一且可读的测试用例ID
        
        Args:
            module: 模块名称，如 "SHORTDRAMA", "PAYMENT" 等
            prefix: ID前缀，默认为 "TC"
            
        Returns:
            格式: TC-MODULE-YYYYMMDDHHMMSS-XXX
            示例: TC-SHORTDRAMA-20241215143022-001
        """
        # 获取当前时间戳（精确到毫秒）
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        # 添加毫秒部分确保唯一性
        milliseconds = now.microsecond // 1000
        timestamp_with_ms = f"{timestamp}{milliseconds:03d}"
        
        # 使用模块作为计数器键，确保同一模块的序列号连续递增
        counter_key = f"{module}"
        
        with self._instance_lock:
            # 获取或初始化序列号
            if counter_key not in self._counters:
                self._counters[counter_key] = 0
            
            # 递增序列号
            self._counters[counter_key] += 1
            sequence = self._counters[counter_key]
            
            # 清理过期的计数器（保留最近1小时的数据）
            self._cleanup_old_counters()
        
        # 生成最终ID
        case_id = f"{prefix}-{module}-{timestamp_with_ms}-{sequence:03d}"
        
        logger.debug(f"Generated case ID: {case_id}")
        return case_id
    
    def _cleanup_old_counters(self):
        """清理过期的计数器，避免内存泄漏"""
        # 由于现在使用模块名作为key，不需要基于时间戳清理
        # 可以设置一个最大计数器值来避免无限增长
        max_counters = 1000  # 最大保留1000个模块的计数器
        
        if len(self._counters) > max_counters:
            # 如果计数器太多，清理一些旧的（这里简化处理，实际可以根据使用频率清理）
            keys_to_remove = list(self._counters.keys())[:len(self._counters) - max_counters]
            for key in keys_to_remove:
                del self._counters[key]
    
    @staticmethod
    def get_sequence_info(case_id: str) -> Optional[Dict[str, str]]:
        """
        解析case_id，获取其组成部分
        
        Args:
            case_id: 测试用例ID
            
        Returns:
            包含prefix, module, timestamp, sequence的字典，如果解析失败返回None
        """
        try:
            parts = case_id.split('-')
            if len(parts) != 4:
                return None
            
            prefix, module, timestamp, sequence = parts
            return {
                'prefix': prefix,
                'module': module,
                'timestamp': timestamp,
                'sequence': sequence
            }
        except Exception as e:
            logger.error(f"Failed to parse case ID: {case_id},error reason: {e}")
            return None
    
    def is_valid_case_id(self, case_id: str) -> bool:
        """
        验证case_id格式是否正确
        
        Args:
            case_id: 测试用例ID
            
        Returns:
            True if valid, False otherwise
        """
        info = self.get_sequence_info(case_id)
        if info is None:
            return False
        
        # 验证序列号长度必须是3位
        return len(info['sequence']) == 3


# 全局实例
case_id_generator = CaseIdGenerator()


def generate_case_id(module: str = "DEFAULT", prefix: str = "TC") -> str:
    """
    便捷函数：生成测试用例ID
    
    Args:
        module: 模块名称
        prefix: ID前缀
        
    Returns:
        生成的测试用例ID
    """
    return case_id_generator.generate_case_id(module, prefix)


def extract_module_from_title(title: str) -> str:
    """
    从测试用例标题中提取模块名称
    
    Args:
        title: 测试用例标题
        
    Returns:
        提取的模块名称，如果无法提取则返回 "DEFAULT"
    """
    # 简单的模块提取逻辑，可以根据实际需求调整
    title_upper = title.upper()
    
    # 常见模块关键词映射
    module_keywords = {
        'SHORTDRAMA': ['短剧', '剧本', 'SHORTDRAMA', 'DRAMA'],
        'PAYMENT': ['支付', 'PAYMENT', 'PAY', 'PAYMENT'],
        'USER': ['用户', 'USER', 'LOGIN', '登录'],
        'ORDER': ['订单', 'ORDER', 'ORDER'],
        'SEARCH': ['搜索', 'SEARCH', 'SEARCH'],
        'CHAT': ['聊天', 'CHAT', 'MESSAGE', '消息']
    }
    
    for module, keywords in module_keywords.items():
        for keyword in keywords:
            if keyword in title_upper:
                return module
    
    return "DEFAULT"


def generate_case_id_from_data(case_data: dict) -> str:
    """
    根据测试用例数据生成ID
    
    Args:
        case_data: 测试用例数据字典
        
    Returns:
        生成的测试用例ID
    """
    # 尝试从数据中提取模块信息
    module = "DEFAULT"
    
    # 优先从module字段中获取
    if 'module' in case_data:
        module = case_data['module'].upper()
    
    # 其次从category中提取模块
    elif 'category' in case_data:
        module = case_data['category'].upper()
    
    # 最后从title中提取模块
    elif 'title' in case_data:
        module = extract_module_from_title(case_data['title'])
    
    return generate_case_id(module)
