"""
TestPilot 通用工具模块
提供常用的工具函数
"""
import os
import re
import time
import socket
import hashlib
import threading
import webbrowser
import pandas as pd
from datetime import datetime
from typing import Any, List, Dict, Mapping
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def _extract_locale_token(raw_locale: str | None) -> str:
    """提取 locale 主 token（兼容 Accept-Language 头）。"""
    raw = (raw_locale or '').strip().lower()
    if not raw:
        return ''
    # 兼容: en-US,en;q=0.9,zh;q=0.8
    first = raw.split(',')[0].strip()
    token = first.split(';')[0].strip()
    return token


def normalize_locale(raw_locale: str | None, default_locale: str = 'zh-CN') -> str:
    """将 locale 归一为 zh-CN / en-US（非中即英）。"""
    token = _extract_locale_token(raw_locale) or _extract_locale_token(default_locale) or 'zh-cn'
    return 'zh-CN' if token.startswith('zh') else 'en-US'


def normalize_language(raw_locale: str | None, default_language: str = 'zh') -> str:
    """将语言归一为 zh / en（非中即英）。"""
    default_locale = 'zh-CN' if default_language == 'zh' else 'en-US'
    return 'zh' if normalize_locale(raw_locale, default_locale).startswith('zh') else 'en'


def resolve_request_locale(request_obj: Any, payload: Mapping[str, Any] | None = None, default_locale: str = 'zh-CN') -> str:
    """从 payload/query/header 解析 locale（非中即英）。"""
    data = payload or {}
    locale = (
        data.get('output_language')
        or data.get('locale')
        or getattr(request_obj, 'args', {}).get('locale')
        or getattr(request_obj, 'headers', {}).get('Accept-Language')
        or default_locale
    )
    return normalize_locale(str(locale), default_locale)


def clean_text(text: str) -> str:
    """
    清理文本内容，移除乱码和无效字符
    
    用于清理从PDF、DOCX等文件解析时产生的乱码字符，确保存储到向量库的数据是干净的
    
    Args:
        text: 需要清理的文本
        
    Returns:
        清理后的文本
    """
    if not text or not isinstance(text, str):
        return ''
    
    # 移除控制字符（保留换行符\n、制表符\t、回车符\r）
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # 移除无效的Unicode字符（替换字符，通常表示编码错误）
    text = text.replace('\uFFFD', '')
    
    # 移除零宽字符
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    
    # 移除私用区字符（通常是乱码）
    text = re.sub(r'[\uE000-\uF8FF]', '', text)
    
    # 移除UTF-8代理对字符（surrogate pairs）- 这些会导致ChromaDB编码错误
    text = re.sub(r'[\uD800-\uDFFF]', '', text)
    
    # 清理多余的空白字符（保留单个空格）
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 移除行首行尾空白
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)
    
    return text.strip()


def get_local_ip():
    """获取本地IP地址

    Returns:
        str: 本地IP地址，如果获取失败则返回None
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        # logger.info(f"获取到当前本地IP是: {local_ip}")
        return local_ip
    except Exception as e:
        logger.error("获取本地IP失败: %s", e)
        return None
    finally:
        if sock is not None:
            sock.close()


def open_browser(ip: str, web_port: int) -> None:
    """Open browser after a delay

    Args:
        ip: IP address to open
        web_port: Port number to use
    """
    time.sleep(1.5)
    webbrowser.open(f'http://{ip}:{web_port}')


def get_network_info():
    """获取网络信息"""
    try:
        local_ip = get_local_ip()
        return {
            'local_ip': local_ip,
            'status': 'connected' if local_ip else 'disconnected'
        }
    except Exception as e:
        logger.error(f"获取网络信息失败: {e}")
        return {
            'local_ip': None,
            'status': 'error'
        }


def generate_id(text):
    """生成基于文本的唯一ID"""
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def format_size(size):
    """格式化文件大小"""
    units = ['B', 'KB', 'MB', 'GB']
    index = 0
    while size >= 1024 and index < 3:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"


def get_file_list(path):
    """获取目录文件列表"""
    files = []
    try:
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            stat = os.stat(full_path)
            files.append({
                "name": item,
                "size": format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
            })
    except Exception as e:
        logger.error(f"无法访问目录: {str(e)}")
    return files


def formate_reqs(reqs: dict) -> list:
    """
    格式化需求字典，返回包含功能和非功能需求的列表
    """
    try:
        functional = reqs.get('functional', []) or []
        non_functional = reqs.get('non_functional', []) or []
        functional_all = []
        for item in functional:
            functional_all.append({"类型": "功能需求", "需求点": item})
        for item in non_functional:
            functional_all.append({"类型": "非功能需求", "需求点": item})
        return functional_all
    except Exception as e:
        logger.error(f"格式化需求异常: {str(e)}")
        return []  # 确保返回值始终是 list


def is_remote_api():
    """判断是否为远程API调用"""
    from config.settings import settings
    
    company = settings.DEFAULT_COMPANY.upper() if settings.DEFAULT_COMPANY else "OPENAI"

    # 远程API列表（会产生费用）
    remote_apis = ["DEEPSEEK", "OPENAI", "GEMINI", "QWEN"]

    # 本地模型列表（不产生费用）
    local_models = ["OLLAMA"]

    if company in remote_apis:
        return True
    elif company in local_models:
        return False
    else:
        # 未知类型，默认按远程API处理（安全起见）
        logger.warning(f"未知的LLM类型: {company}，按远程API处理")
        return True


class CaseNumberManager:
    """统一的测试用例编号管理器"""
    _lock = threading.Lock()  # 添加类级别的线程锁

    @staticmethod
    def clean_module_name(module_name: str) -> str:
        """清理模块名，只保留中英文和数字"""
        if not module_name:
            return "MODULE"
        cleaned = re.sub(r'[^0-9A-Za-z\u4e00-\u9fa5]', '', str(module_name))[:6]
        return cleaned if cleaned else "MODULE"

    @staticmethod
    def generate_batch_case_id(module_name: str, batch_index: int, case_index: int) -> str:
        """生成批次编号：TC-{模块名}-{批次号}-{序号}"""
        module_clean = CaseNumberManager.clean_module_name(module_name)
        return f"TC-{module_clean}-{batch_index:02d}-{case_index:02d}"

    @staticmethod
    def generate_display_case_id(original_id: str) -> str:
        """生成显示编号：只返回原始编号"""
        return original_id

    @staticmethod
    def extract_original_id(case_id: str) -> str:
        """提取原始编号，去除显示格式"""
        if isinstance(case_id, str):
            # 去除显示格式: "TC-LOGIN-01 (001)" -> "TC-LOGIN-01"
            return case_id.split(' (')[0]
        return case_id

    @staticmethod
    def renumber_cases_for_batch(cases_df: pd.DataFrame, batch_index: int) -> pd.DataFrame:
        """为批次处理重新编号"""
        if cases_df.empty:
            return cases_df

        new_ids = []
        for idx, (_, row) in enumerate(cases_df.iterrows()):
            module_name = row.get('模块名称', 'UNKNOWN')
            case_id = CaseNumberManager.generate_batch_case_id(module_name, batch_index + 1, idx + 1)
            new_ids.append(case_id)

        cases_df = cases_df.copy()
        cases_df['用例编号'] = new_ids
        return cases_df

    @staticmethod
    def renumber_cases_for_display(cases_df: pd.DataFrame) -> pd.DataFrame:
        """为显示处理重新编号，并添加全局序号列 - 线程安全版本"""
        if cases_df.empty:
            return cases_df

        with CaseNumberManager._lock:  # 使用线程锁
            # 创建临时列用于排序
            cases_df = cases_df.copy()

            # 提取用例编号中的数字部分用于排序
            def extract_sort_key(case_id):
                if isinstance(case_id, str):
                    # 提取TC-PLAYER-08中的08部分
                    match = re.search(r'-(\d+)$', case_id)
                    if match:
                        return int(match.group(1))
                return 999  # 无法解析的放在最后

            cases_df['_sort_key'] = cases_df['用例编号'].apply(extract_sort_key)

            # 按排序键排序
            cases_df = cases_df.sort_values('_sort_key')

            new_ids, global_numbers = [], []
            for idx, (_, row) in enumerate(cases_df.iterrows()):
                current_id = row['用例编号']
                # 直接使用原始编号，不添加括号数字
                new_ids.append(current_id)
                global_numbers.append(idx + 1)

            cases_df['原始编号'] = cases_df['用例编号']
            cases_df['用例编号'] = new_ids
            cases_df['全局序号'] = global_numbers

            # 删除临时排序列
            cases_df = cases_df.drop('_sort_key', axis=1)

            return cases_df

    @staticmethod
    def smart_deduplicate(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """智能去重，基于原始编号比较"""
        if existing_cases.empty:
            return new_cases

        if new_cases.empty:
            return pd.DataFrame()

        existing_original_ids = set(
            CaseNumberManager.extract_original_id(case_id) for case_id in existing_cases['用例编号'].tolist()
        )
        unique_mask = ~new_cases['用例编号'].apply(CaseNumberManager.extract_original_id).isin(existing_original_ids)
        return new_cases[unique_mask]

    @staticmethod
    def merge_cases(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """合并测试用例，自动去重"""
        unique_new_cases = CaseNumberManager.smart_deduplicate(existing_cases, new_cases)

        if unique_new_cases.empty:
            return existing_cases
        if existing_cases.empty:
            return unique_new_cases

        return pd.concat([existing_cases, unique_new_cases], ignore_index=True)

    @staticmethod
    def renumber_cases_sequential(cases_df: pd.DataFrame) -> pd.DataFrame:
        """重新整理编号，确保序号连贯 - 修复编号不一致问题"""
        if cases_df.empty:
            return cases_df

        cases_df = cases_df.copy()
        cases_df = cases_df.sort_values(['功能模块', '用例编号'])

        new_cases = []
        global_index = 1  # 全局连续编号

        for module_name, group in cases_df.groupby('功能模块'):
            module_clean = CaseNumberManager.clean_module_name(str(module_name))
            # 使用全局连续编号，而不是模块内编号
            for idx, (_, row) in enumerate(group.iterrows()):
                new_case_id = f"TC-{module_clean}-{global_index:02d}"
                new_row = row.copy()
                new_row['用例编号'] = new_case_id
                new_cases.append(new_row)
                global_index += 1  # 全局编号递增

        return pd.DataFrame(new_cases)

    @staticmethod
    def merge_cases_with_renumbering(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """合并测试用例，自动去重并重新整理编号"""
        merged_cases = CaseNumberManager.merge_cases(existing_cases, new_cases)
        return CaseNumberManager.renumber_cases_sequential(merged_cases)

    @staticmethod
    def merge_cases_optimized(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """优化的用例合并，支持大量数据"""
        if existing_cases.empty:
            return new_cases

        if new_cases.empty:
            return pd.DataFrame()

        # 使用更高效的去重算法
        existing_ids = set(existing_cases['用例编号'].tolist())
        unique_mask = ~new_cases['用例编号'].isin(existing_ids)
        unique_new_cases = new_cases[unique_mask]

        if unique_new_cases.empty:
            return existing_cases

        # 预分配索引，避免ignore_index
        max_index = existing_cases.index.max() if not existing_cases.empty else -1
        unique_new_cases.index = range(max_index + 1, max_index + 1 + len(unique_new_cases))

        return pd.concat([existing_cases, unique_new_cases])

    @staticmethod
    def merge_cases_with_renumbering_optimized(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """优化的合并和重新编号"""
        merged_cases = CaseNumberManager.merge_cases_optimized(existing_cases, new_cases)
        return CaseNumberManager.renumber_cases_sequential(merged_cases)

    @staticmethod
    def process_large_dataset(cases_df: pd.DataFrame, chunk_size: int = 1000) -> pd.DataFrame:
        """处理大数据集的分块处理"""
        if len(cases_df) <= chunk_size:
            return CaseNumberManager.renumber_cases_sequential(cases_df)

        # 分块处理
        chunks = [cases_df[i:i + chunk_size] for i in range(0, len(cases_df), chunk_size)]
        processed_chunks = []

        for i, chunk in enumerate(chunks):
            # 为每个块重新编号
            chunk = CaseNumberManager.renumber_cases_sequential(chunk)
            processed_chunks.append(chunk)

        # 合并所有块
        return pd.concat(processed_chunks, ignore_index=True)

    @staticmethod
    def merge_cases_with_performance_monitoring(existing_cases: pd.DataFrame, new_cases: pd.DataFrame) -> pd.DataFrame:
        """带性能监控的用例合并"""
        from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor

        monitor = get_performance_monitor()
        start_time = time.time()

        try:
            result = CaseNumberManager.merge_cases_optimized(existing_cases, new_cases)

            # 更新性能统计
            processing_time = time.time() - start_time
            monitor.update_processed_count(len(new_cases))

            logger.info(f"用例合并完成: {len(new_cases)} 个新用例, 耗时: {processing_time:.3f} 秒")
            return result

        except Exception as e:
            logger.error(f"用例合并异常: {e}")
            raise

    @staticmethod
    def batch_process_cases(cases_list: List[Dict], batch_size: int = 100) -> pd.DataFrame:
        """批量处理用例列表"""
        from utils.utils_performance_monitoring.performance_monitor import get_performance_monitor

        monitor = get_performance_monitor()
        all_cases = pd.DataFrame()

        try:
            # 分批处理
            for i in range(0, len(cases_list), batch_size):
                batch = cases_list[i:i + batch_size]
                batch_df = pd.DataFrame(batch)

                # 重新编号
                batch_df = CaseNumberManager.renumber_cases_sequential(batch_df)

                # 合并到总结果
                all_cases = pd.concat([all_cases, batch_df], ignore_index=True)

                # 更新性能统计
                monitor.update_processed_count(len(batch))

                logger.info(f"处理批次 {i // batch_size + 1}: {len(batch)} 个用例")

            return all_cases

        except Exception as e:
            logger.error(f"批量处理异常: {e}")
            raise

    @staticmethod
    def smart_deduplicate_with_content(existing_cases: pd.DataFrame, new_cases: pd.DataFrame,
                                       content_threshold: float = 0.8) -> pd.DataFrame:
        """
        智能去重：结合编号去重和内容去重

        Args:
            existing_cases: 现有用例DataFrame
            new_cases: 新用例DataFrame
            content_threshold: 内容相似度阈值

        Returns:
            去重后的新用例DataFrame
        """
        from utils.utils_document_processing.content_similarity import create_content_detector

        if existing_cases.empty:
            return new_cases

        if new_cases.empty:
            return pd.DataFrame()

        # 1. 先进行编号去重
        unique_new_cases = CaseNumberManager.smart_deduplicate(existing_cases, new_cases)

        if unique_new_cases.empty:
            return pd.DataFrame()

        # 2. 再进行内容去重
        content_detector = create_content_detector(content_threshold)

        # 合并现有用例和新用例进行内容去重
        combined_cases = pd.concat([existing_cases, unique_new_cases], ignore_index=True)

        # 内容去重
        deduplicated_cases = content_detector.remove_duplicates_from_dataframe(combined_cases)

        # 只返回新用例中未被去重的部分
        if len(deduplicated_cases) > len(existing_cases):
            return deduplicated_cases.iloc[len(existing_cases):].reset_index(drop=True)
        else:
            return pd.DataFrame()

    @staticmethod
    def merge_cases_with_content_dedup(existing_cases: pd.DataFrame, new_cases: pd.DataFrame,
                                       content_threshold: float = 0.8) -> pd.DataFrame:
        """
        合并测试用例，自动去重（编号+内容）

        Args:
            existing_cases: 现有用例
            new_cases: 新用例
            content_threshold: 内容相似度阈值

        Returns:
            合并并去重后的用例DataFrame
        """
        # 使用增强的去重方法
        unique_new_cases = CaseNumberManager.smart_deduplicate_with_content(
            existing_cases, new_cases, content_threshold
        )

        if unique_new_cases.empty:
            return existing_cases
        if existing_cases.empty:
            return unique_new_cases

        # 合并并重新编号
        merged_cases = pd.concat([existing_cases, unique_new_cases], ignore_index=True)
        return CaseNumberManager.renumber_cases_sequential(merged_cases)
