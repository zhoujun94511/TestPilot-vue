#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
文档预处理器模块
负责文档解析、模块提取、复杂度评估等功能
"""
import re
from pathlib import Path
from typing import List, Dict, Optional
from utils.utils_core.logger import get_logger
from utils.utils_document_processing.parser import file_loader
from utils.utils_business_logic.complexity_scorer import assess_complexity, ComplexityScorer
from utils.utils_config_management.optimization_config import get_optimization_config

logger = get_logger(__name__)


class DocumentPreprocessor:
    def __init__(self):
        opt_config = get_optimization_config().get_config()
        self.supported_formats = opt_config.get(
            "supported_formats",
            ['.txt', '.md', '.docx', '.csv', '.json', '.xlsx', '.pdf', '.yaml', '.yml']
        )
        self.max_cases_per_batch = opt_config.get("max_case_num", 3)

        # 使用知识库初始化 ComplexityScorer
        self._kb = opt_config.get("knowledge_base", {}) or {}
        risk_map = opt_config.get("risk_weight_map", None)

        try:
            self.complexity_scorer = ComplexityScorer.from_knowledge_base(
                self._kb, profile="balanced", risk_weight_map=risk_map
            )
        except Exception as e:
            logger.warning(f"初始化复杂度评估器失败，使用默认配置: {e}")
            self.complexity_scorer = ComplexityScorer()

        # 动态关键词池（用于回退抽取模块）
        self._fallback_keywords = self._build_fallback_keywords_from_kb(self._kb)

    def analyze_document(self, file_path: str) -> Dict:
        """
        分析文档内容，评估测试用例生成需求
        """
        try:
            logger.info(f"开始分析文档: {file_path}")

            # 检查格式
            ext = Path(file_path).suffix.lower()
            if ext not in self.supported_formats:
                logger.warning(f"文件格式不支持: {ext}")
                return {
                    'error': f"暂不支持解析该格式: {ext}",
                    'total_modules': 0,
                    'estimated_cases': 0,
                    'batches_needed': 0,
                    'modules': [],
                    'complexity': 'unknown'
                }

            # 加载文档
            try:
                result = file_loader(file_path)
                if not isinstance(result, (list, tuple)) or len(result) < 3:
                    raise ValueError("file_loader 返回结构异常")
                text_list, doc_splits, metadata_list = result
            except Exception as fe:
                logger.error(f"加载文件失败: {fe}")
                return {
                    'error': f"文件解析失败: {fe}",
                    'total_modules': 0,
                    'estimated_cases': 0,
                    'batches_needed': 0,
                    'modules': [],
                    'complexity': 'unknown'
                }

            full_content = " ".join(text_list) if text_list else ""

            # 解析模块
            modules = self._extract_modules(full_content)

            # 估算测试用例数量
            estimated_cases = self._estimate_test_cases(modules, full_content)

            # 计算批次数
            batches_needed = (estimated_cases + self.max_cases_per_batch - 1) // self.max_cases_per_batch \
                if estimated_cases > 0 else 0

            # 复杂度评估
            try:
                complexity = assess_complexity(
                    modules,
                    estimated_cases,
                    content=full_content,
                    profile="balanced",
                    return_details=True
                )
            except Exception as e:
                logger.warning(f"复杂度评估失败: {e}")
                complexity = "unknown"

            result = {
                'total_modules': len(modules),
                'estimated_cases': estimated_cases,
                'batches_needed': batches_needed,
                'modules': modules,
                'complexity': complexity,
                'file_size': len(full_content),
                'chunks_count': len(doc_splits)
            }

            logger.info(f"文档分析完成: {result}")
            return result

        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return {
                'error': str(e),
                'total_modules': 0,
                'estimated_cases': 0,
                'batches_needed': 0,
                'modules': [],
                'complexity': 'unknown'
            }

    def _extract_modules(self, content: str) -> List[Dict]:
        """提取模块信息：优先标题/结构，其次知识库关键词，最后段落回退"""
        if not content:
            return []

        modules: List[Dict] = []

        # 如果内容包含换行符，按行处理
        if '\n' in content:
            lines = content.split('\n')
            title_patterns = [
                r'^#\s+(.+)$',  # 一级标题
                r'^##\s+(.+)$',  # 二级标题
                r'^###\s+(.+)$',  # 三级标题
                r'^\d+\.\s+(.+)$',  # 数字列表
                r'^[一二三四五六七八九十]+、(.+)$',  # 中文数字标题
            ]
        else:
            # 如果内容被合并成一行，重构内容，在标题前添加换行符
            content = re.sub(r'(\s+)(#+\s+)', r'\n\2', content)
            content = re.sub(r'(\s+)(\d+\.\s+)', r'\n\2', content)
            content = re.sub(r'(\s+)([一二三四五六七八九十]+、)', r'\n\2', content)
            content = re.sub(r'(\s+)(###\s+)', r'\n\2', content)  # 三级标题
            content = re.sub(r'(\s+)(##\s+)', r'\n\2', content)  # 二级标题
            lines = content.split('\n')
            title_patterns = [
                r'^#\s+(.+)$',  # 一级标题
                r'^##\s+(.+)$',  # 二级标题
                r'^###\s+(.+)$',  # 三级标题
                r'^\d+\.\s+(.+)$',  # 数字列表
                r'^[一二三四五六七八九十]+、(.+)$',  # 中文数字标题
            ]

        for line in lines:
            line = line.strip()
            if not line:
                continue
            for pattern in title_patterns:
                try:
                    match = re.search(pattern, line[:500])
                    if match:
                        module_name = match.group(1).strip()
                        if self._is_valid_module(module_name):
                            try:
                                description = self._extract_module_description(content, module_name)
                                submodules = self._extract_submodules(content, module_name)
                                modules.append({
                                    'name': module_name,
                                    'type': 'main',
                                    'description': description,
                                    'submodules': submodules
                                })
                            except Exception as desc_err:
                                logger.warning(f"提取描述/子模块失败: {desc_err}")
                                # 即使描述/子模块提取失败，也添加模块
                                modules.append({
                                    'name': module_name,
                                    'type': 'main',
                                    'description': f"{module_name}功能模块",
                                    'submodules': []
                                })
                except Exception as re_err:
                    logger.warning(f"正则匹配失败: {re_err}")
                    continue

        # 回退：基于知识库关键词匹配
        if not modules:
            modules = self._extract_by_keywords(content, self._fallback_keywords)

        # 仍为空：段落启发式
        if not modules:
            modules = self._extract_by_paragraphs(content)

        return modules

    def _extract_by_keywords(self, content: str, keywords: Optional[List[str]] = None) -> List[Dict]:
        """基于知识库动态关键词提取模块"""
        if not content:
            return []
        kw_list = keywords or self._fallback_keywords or []
        seen = set()
        modules: List[Dict] = []
        for kw in kw_list:
            if not kw or kw in seen:
                continue
            hit = (kw in content) or (kw.lower() in content.lower())
            if hit:
                modules.append({
                    'name': kw,
                    'type': 'keyword',
                    'description': f"{kw}相关功能模块",
                    'submodules': []
                })
                seen.add(kw)
        return modules

    @staticmethod
    def _collect_names_from_group_items(group_items: List[Dict]) -> List[str]:
        out: List[str] = []
        for item in group_items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            en = item.get("en")
            aliases = item.get("aliases", [])
            subs = item.get("sub", [])
            if name:
                out.append(name)
            if en:
                out.append(en)
            for a in aliases or []:
                if a:
                    out.append(a)
            for s in subs or []:
                if s:
                    out.append(s)
        return out

    def _build_fallback_keywords_from_kb(self, kb: Dict) -> List[str]:
        """从 knowledge_base 构建用于回退的关键词池"""
        pool: List[str] = []
        # functional_keywords
        for item in kb.get("functional_keywords", {}).get("items", []):
            pool.extend(self._collect_names_from_group_items([item]))
        # core_features
        for group_items in kb.get("core_features", {}).get("groups", {}).values():
            pool.extend(self._collect_names_from_group_items(group_items))
        # 去重并按长度降序
        pool = sorted(set([p for p in pool if p]), key=lambda x: len(x), reverse=True)
        return pool

    @staticmethod
    def _is_valid_module(name: str) -> bool:
        if not name:
            return False
        if len(name) < 2 or len(name) > 200:
            return False
        if name in ['目录', '概述', '总结', '附录']:
            return False
        return True

    @staticmethod
    def _extract_module_description(content: str, module_name: str) -> str:
        if not content or not module_name:
            return f"{module_name}功能模块"
        try:
            pattern = rf'{re.escape(module_name)}[：:]\s*(.+?)(?=\n\n|\n#|\n\d+\.|$)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                desc = match.group(1).strip()
                return desc[:200] + "..." if len(desc) > 200 else desc
        except Exception as e:
            logger.warning(f"提取描述失败: {e}")
        return f"{module_name}功能模块"

    @staticmethod
    def _extract_submodules(content: str, module_name: str) -> List[str]:
        if not content or not module_name:
            return []
        submodules: List[str] = []
        try:
            pattern = rf'{re.escape(module_name)}.*?\n((?:\s*[-*]\s*.+\n?)*)'
            match = re.search(pattern, content[:5000], re.DOTALL)  # 限制搜索窗口
            if match:
                sub_items = match.group(1)[:2000]
                for line in sub_items.split('\n'):
                    line = re.sub(r'^\s*[-*]\s*', '', line).strip()
                    if line and len(line) < 30:
                        submodules.append(line)
        except Exception as e:
            logger.warning(f"提取子模块失败: {e}")
        return submodules[:5]

    @staticmethod
    def _extract_by_paragraphs(content: str) -> List[Dict]:
        """基于段落结构提取模块"""
        if not content:
            return []
        paragraphs = content.split('\n\n')[:500]  # 限制最多500段
        modules: List[Dict] = []
        for i, para in enumerate(paragraphs):
            if len(para.strip()) > 50:
                first_line = para.split('\n')[0].strip()
                if len(first_line) < 20:
                    modules.append({
                        'name': f"模块{i + 1}: {first_line}",
                        'type': 'paragraph',
                        'description': para[:100] + "..." if len(para) > 100 else para,
                        'submodules': []
                    })
        return modules[:5]

    def _estimate_test_cases(self, modules: List[Dict], content: str) -> int:
        """
        根据模块 + 知识库风险标签 + 文档规模来估算测试用例数量
        """
        if not modules:
            return 0
        if not isinstance(content, str):
            content = ""

        # 基础：每个模块至少 3 个用例
        base_cases = len(modules) * 3

        # 风险等级映射
        risk_weight_map = {"critical": 10, "high": 7, "medium": 4, "low": 2}

        functional_groups = self._kb.get("functional_keywords", {}).get("items", [])
        core_groups = self._kb.get("core_features", {}).get("groups", {})

        # 如果 groups 是字典，转换为列表
        if isinstance(functional_groups, dict):
            functional_groups = list(functional_groups.values())
        if isinstance(core_groups, dict):
            core_groups = list(core_groups.values())

        # 确保都是列表
        if not isinstance(functional_groups, list):
            functional_groups = []
        if not isinstance(core_groups, list):
            core_groups = []

        for module in modules:
            name = module.get("name", "")
            if not name:
                continue
            matched_risk = 0
            for group in (functional_groups + core_groups):
                # 确保 group 是字典
                if not isinstance(group, dict):
                    continue
                for item in group.get("items", []):
                    # 确保 item 是字典
                    if not isinstance(item, dict):
                        continue
                    kw_list = [item.get("name"), item.get("en")] \
                              + item.get("aliases", []) + item.get("sub", [])
                    kw_list = [k for k in kw_list if k]
                    if any(kw in name or kw.lower() in name.lower() for kw in kw_list):
                        risk = item.get("risk", "medium").lower()
                        matched_risk = max(matched_risk, risk_weight_map.get(risk, 0))
            base_cases += matched_risk

        # 根据文档规模调整
        length = len(content)
        if length > 20000:
            base_cases = int(base_cases * 2.5)
        elif length > 10000:
            base_cases = int(base_cases * 2.0)
        elif length > 5000:
            base_cases = int(base_cases * 1.5)

        return min(base_cases, 300)

    def create_batch_plan(self, analysis_result: Dict) -> List[Dict]:
        if analysis_result.get('error'):
            return []

        modules = analysis_result.get('modules', [])
        batches_needed = analysis_result.get('batches_needed', 0)

        if not batches_needed or batches_needed <= 1:
            return [{
                'batch_id': 1,
                'modules': modules,
                'estimated_cases': analysis_result.get('estimated_cases', 0),
                'description': '单批次处理'
            }]

        batches: List[Dict] = []
        modules_per_batch = max(1, len(modules) // batches_needed)

        for i in range(batches_needed):
            start_idx = i * modules_per_batch
            end_idx = start_idx + modules_per_batch if i < batches_needed - 1 else len(modules)
            batch_modules = modules[start_idx:end_idx]
            batch_cases = sum(len(m.get('submodules', [])) * 2 + 3 for m in batch_modules)
            batches.append({
                'batch_id': i + 1,
                'modules': batch_modules,
                'estimated_cases': min(batch_cases, self.max_cases_per_batch),
                'description': f'第{i + 1}批次: {len(batch_modules)}个模块'
            })

        return batches

    @staticmethod
    def process_modules(modules: List[Dict]) -> List[Dict]:
        if not modules:
            return []
        processed_modules: List[Dict] = []
        for module in modules:
            if isinstance(module, dict) and 'name' in module:
                processed_modules.append({
                    'name': module['name'],
                    'type': module.get('type', 'unknown'),
                    'description': module.get('description', ''),
                    'submodules': module.get('submodules', [])
                })
        return processed_modules
