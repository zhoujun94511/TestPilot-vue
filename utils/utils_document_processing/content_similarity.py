#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
测试用例内容相似度检测模块
基于文本相似度进行智能去重，防止用例内容重复
"""
import re
import hashlib
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
import pandas as pd
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class UnionFind:
    """并查集工具类，用于簇去重"""

    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int):
        root_x, root_y = self.find(x), self.find(y)
        if root_x != root_y:
            self.parent[root_y] = root_x


class ContentSimilarityDetector:
    """测试用例内容相似度检测器"""

    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化相似度检测器
        """
        self.similarity_threshold = similarity_threshold
        self.content_hashes = set()

        # 字段名映射：支持中英文字段名
        self.FIELD_MAPPING = {
            'title': ['title', '标题'],
            'steps': ['steps', '测试步骤'],
            'expected': ['expected', '预期结果'],
            'preconditions': ['preconditions', '前置条件'],
            'module': ['module', '功能模块'],
            'priority': ['priority', '优先级'],
            'test_type': ['test_type', '测试类型'],
            'test_method': ['test_method', '测试方法']
        }

        # 字段权重配置
        self.weights = {
            'title': 0.4,
            'steps': 0.3,
            'expected': 0.2,
            'preconditions': 0.1
        }

    def extract_content_features(self, case: Dict) -> Dict:
        """提取测试用例的关键特征用于相似度比较"""

        def get_field_value(field_names):
            values = []
            for name in field_names:
                if name in case and case[name]:
                    values.append(str(case[name]))
            return " ".join(values)

        features = {field: self._normalize_text(get_field_value(names))
                    for field, names in self.FIELD_MAPPING.items()}
        features['content_hash'] = self._generate_content_hash(case)
        return features

    @staticmethod
    def _normalize_text(text: str) -> str:
        """文本标准化处理"""
        if not text:
            return ''
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\u4e00-\u9fa5\s]', '', text)
        return text.strip()

    def _generate_content_hash(self, case: Dict) -> str:
        """生成测试用例内容的哈希值（包含所有核心字段）"""

        def get_field_value(field_names):
            values = []
            for name in field_names:
                if name in case and case[name]:
                    values.append(str(case[name]))
            return " ".join(values)

        content_parts = [get_field_value(names) for names in self.FIELD_MAPPING.values()]
        normalized_content = '|'.join([self._normalize_text(part) for part in content_parts])
        return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()

    def calculate_similarity(self, case1: Dict, case2: Dict) -> float:
        """计算两个测试用例的相似度"""
        features1 = self.extract_content_features(case1)
        features2 = self.extract_content_features(case2)

        if features1['content_hash'] == features2['content_hash']:
            return 1.0

        similarities = [
            ('title', self._text_similarity(features1['title'], features2['title']), self.weights['title']),
            ('steps', self._text_similarity(features1['steps'], features2['steps']), self.weights['steps']),
            ('expected', self._text_similarity(features1['expected'], features2['expected']), self.weights['expected']),
            ('preconditions', self._text_similarity(features1['preconditions'], features2['preconditions']), self.weights['preconditions']),
        ]

        total_weight = sum(weight for _, _, weight in similarities)
        return sum(sim * weight for _, sim, weight in similarities) / total_weight

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def find_duplicate_cases(self, cases: List[Dict]) -> List[Tuple[int, int, float]]:
        """
        在用例列表中找到重复的用例对（哈希分桶 + 跨桶比较）
        """
        duplicates = []

        # 按哈希分桶
        hash_buckets: Dict[str, List[int]] = {}
        for i, case in enumerate(cases):
            h = self._generate_content_hash(case)
            hash_buckets.setdefault(h, []).append(i)

        # 1. 同一哈希桶内 → 直接判定为重复
        for indices in hash_buckets.values():
            if len(indices) > 1:
                for i in range(len(indices)):
                    for j in range(i + 1, len(indices)):
                        duplicates.append((indices[i], indices[j], 1.0))
                        logger.debug(f"完全重复用例: 索引{indices[i]} 和 索引{indices[j]}")

        # 2. 不同哈希桶之间 → 相似度计算
        bucket_keys = list(hash_buckets.keys())
        for i in range(len(bucket_keys)):
            for j in range(i + 1, len(bucket_keys)):
                for idx1 in hash_buckets[bucket_keys[i]]:
                    for idx2 in hash_buckets[bucket_keys[j]]:
                        sim = self.calculate_similarity(cases[idx1], cases[idx2])
                        if sim >= self.similarity_threshold:
                            duplicates.append((idx1, idx2, sim))
                            logger.debug(f"相似用例: 索引{idx1} 和 索引{idx2}, 相似度: {sim:.3f}")

        return duplicates

    def remove_duplicates_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """从DataFrame中移除重复的测试用例，按簇去重"""
        if df.empty:
            return df

        logger.info(f"开始内容去重检查，原始用例数量: {len(df)}")
        cases = df.to_dict('records')
        duplicates = self.find_duplicate_cases(cases)

        if not duplicates:
            logger.info("未发现内容重复的用例")
            return df

        # 用并查集合并簇
        uf = UnionFind(len(cases))
        for idx1, idx2, _ in duplicates:
            uf.union(idx1, idx2)

        clusters: Dict[int, List[int]] = {}
        for idx in range(len(cases)):
            root = uf.find(idx)
            clusters.setdefault(root, []).append(idx)

        indices_to_remove = set()
        for root, members in clusters.items():
            for m in members[1:]:  # 保留簇内第一个
                indices_to_remove.add(m)
                logger.info(f"标记删除重复用例: 索引{m} (属于簇 {root})")

        if indices_to_remove:
            df_cleaned = df.drop(df.index[list(indices_to_remove)])
            logger.info(f"内容去重完成，删除 {len(indices_to_remove)} 个重复用例，剩余 {len(df_cleaned)} 个用例")
            return df_cleaned
        return df

    def get_similarity_report(self, cases: List[Dict]) -> Dict:
        """生成相似度检测报告"""
        duplicates = self.find_duplicate_cases(cases)
        report = {
            'total_cases': len(cases),
            'duplicate_pairs': len(duplicates),
            'duplicate_details': []
        }
        for idx1, idx2, similarity in duplicates:
            case1 = cases[idx1]
            case2 = cases[idx2]
            report['duplicate_details'].append({
                'index1': idx1,
                'index2': idx2,
                'similarity': similarity,
                'case1_title': case1.get('title', case1.get('标题', '')),
                'case2_title': case2.get('title', case2.get('标题', '')),
                'case1_id': case1.get('case_id', case1.get('用例编号', '')),
                'case2_id': case2.get('case_id', case2.get('用例编号', ''))
            })
        return report


def create_content_detector(threshold: float = 0.8) -> ContentSimilarityDetector:
    """创建内容相似度检测器"""
    return ContentSimilarityDetector(similarity_threshold=threshold)
