#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
复杂度评估器模块
基于需求文档和模块信息评估测试复杂度
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from statistics import mean
from typing import Dict, List, Optional, Tuple, Union
from utils.utils_config_management.optimization_config import get_optimization_config
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComplexityResult:
    label: str
    score: int
    features: Dict[str, float]
    thresholds: Dict[str, int]
    notes: List[str]

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["features"] = {k: (round(v, 4) if isinstance(v, float) else v)
                         for k, v in d["features"].items()}
        return d


class ComplexityScorer:
    """
    复杂度打分器（支持从 knowledge_base.json 动态加载关键字）
    """

    # 默认兜底关键字权重
    DEFAULT_KEYWORD_WEIGHTS: Dict[str, int] = {
        "登录": 10, "注册": 6, "支付": 18, "权限": 14,
        "风控": 12, "视频": 9, "搜索": 7, "订单": 8, "消息": 6,
    }

    # 默认风险信号关键字（兜底）
    DEFAULT_RISK_KEYWORDS: Tuple[str, ...] = (
        "合规", "合规性", "隐私", "GDPR", "CCPA", "PCI", "加密", "脱敏", "风控", "风控规则",
        "审计", "风险评估", "KYC", "AML", "反洗钱", "权限矩阵", "最小权限", "多因子", "MFA",
        "幂等", "回滚", "补偿", "重试", "降级", "熔断", "限流", "监控", "告警",
    )

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "cases": 1.0,
        "module_count": 2.0,
        "submodules_sum": 1.0,
        "submodules_avg": 1.0,
        "desc_len_sum": 1 / 200.0,
        "desc_len_avg": 1 / 300.0,
        "domain_keywords": 1.0,
        "risk_signals": 2.0,
        "dependency_edges": 1.5,
        "dependency_centrality": 10.0,
        "doc_headings": 0.8,
        "doc_bullets": 0.6,
        "doc_tables": 1.2,
        "doc_codeblocks": 0.6,
    }

    DEFAULT_THRESHOLDS: Dict[str, int] = {
        "very_simple": 20,
        "simple": 50,
        "medium": 100,
        "complex": 200,
    }

    PROFILES: Dict[str, Dict[str, int]] = {
        "aggressive": {"very_simple": 15, "simple": 40, "medium": 80, "complex": 160},
        "conservative": {"very_simple": 25, "simple": 60, "medium": 120, "complex": 240},
        "balanced": DEFAULT_THRESHOLDS,
    }

    def __init__(
        self,
        keyword_weights: Optional[Dict[str, int]] = None,
        risk_keywords: Optional[Tuple[str, ...]] = None,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, int]] = None,
        profile: str = "balanced",
        risk_weight_map: Optional[Dict[str, int]] = None,
    ) -> None:
        self.keyword_weights = keyword_weights or self.DEFAULT_KEYWORD_WEIGHTS.copy()
        self.risk_keywords = risk_keywords or self.DEFAULT_RISK_KEYWORDS
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.thresholds = thresholds or self.PROFILES.get(profile, self.DEFAULT_THRESHOLDS).copy()
        self.risk_weight_map = risk_weight_map or {
            "low": 1, "medium": 4, "high": 8, "critical": 15
        }

    @classmethod
    def from_knowledge_base(
        cls,
        kb: Optional[Dict] = None,
        profile: str = "balanced",
        risk_weight_map: Optional[Dict[str, int]] = None,
    ) -> "ComplexityScorer":
        """
        从 knowledge_base.json 构造 ComplexityScorer
        """
        if kb is None:
            kb = get_optimization_config().get_config().get("knowledge_base", {})

        kw_weights: Dict[str, int] = {}
        rmap = risk_weight_map or {"low": 1, "medium": 4, "high": 8, "critical": 15}

        def add_item(kb_item: Dict):
            risk = (kb_item.get("risk") or "medium").lower()
            w = int(rmap.get(risk, 4))
            if kb_item.get("name"):
                kw_weights[kb_item["name"]] = max(kw_weights.get(kb_item["name"], 0), w)
            if kb_item.get("en"):
                kw_weights[kb_item["en"]] = max(kw_weights.get(kb_item["en"], 0), w)
            for alias in kb_item.get("aliases", []):
                kw_weights[alias] = max(kw_weights.get(alias, 0), w)
            for sub in kb_item.get("sub", []):
                kw_weights[sub] = max(kw_weights.get(sub, 0), w)

        # functional_keywords
        for item in kb.get("functional_keywords", {}).get("items", []):
            add_item(item)

        # core_features
        for group_items in kb.get("core_features", {}).get("groups", {}).values():
            for item in group_items:
                add_item(item)

        # 如果 JSON 没加载到，fallback
        if not kw_weights:
            kw_weights = cls.DEFAULT_KEYWORD_WEIGHTS.copy()

        return cls(keyword_weights=kw_weights, profile=profile, risk_weight_map=rmap)

    def assess(
            self,
            modules: List[Dict],
            estimated_cases: int,
            content: str = "",
            return_details: bool = False,
    ) -> Union[ComplexityResult, str]:
        if not modules or estimated_cases is None or estimated_cases < 0:
            result = ComplexityResult("unknown", 0, {}, self.thresholds.copy(), ["no-modules-or-invalid-cases"])
            return result if return_details else result.label

        features, notes = self._compute_features(modules, estimated_cases, content)
        score = self._score(features)
        label = self._map_score(score)
        result = ComplexityResult(
            label=label,
            score=int(round(score)),
            features=features,
            thresholds=self.thresholds.copy(),
            notes=notes,
        )
        return result if return_details else result.label

    def _compute_features(self, modules: List[Dict], estimated_cases: int, content: str):
        notes: List[str] = []
        names = [m.get("name", "").strip() for m in modules if isinstance(m, dict)]
        descriptions = [m.get("description", "") or "" for m in modules]
        submodules_lists = [m.get("submodules", []) or [] for m in modules]

        module_count = len(modules)
        submodules_sum = sum(len(s) for s in submodules_lists)
        submodules_avg = (submodules_sum / module_count) if module_count else 0.0

        desc_lens = [len(d) for d in descriptions]
        desc_len_sum = float(sum(desc_lens))
        desc_len_avg = float(mean(desc_lens)) if desc_lens else 0.0

        domain_kw_score = self._domain_keyword_score(names)
        risk_score = self._risk_signal_score(descriptions, content)
        dep_edges, centrality = self._dependency_metrics(names, descriptions)
        doc_headings, doc_bullets, doc_tables, doc_codeblocks = self._doc_structure(content)

        feats: Dict[str, float] = {
            "cases": float(estimated_cases),
            "module_count": float(module_count),
            "submodules_sum": float(submodules_sum),
            "submodules_avg": float(submodules_avg),
            "desc_len_sum": float(desc_len_sum),
            "desc_len_avg": float(desc_len_avg),
            "domain_keywords": float(domain_kw_score),
            "risk_signals": float(risk_score),
            "dependency_edges": float(dep_edges),
            "dependency_centrality": float(centrality),
            "doc_headings": float(doc_headings),
            "doc_bullets": float(doc_bullets),
            "doc_tables": float(doc_tables),
            "doc_codeblocks": float(doc_codeblocks),
        }

        if domain_kw_score > 0:
            notes.append("domain-keywords-detected")
        if risk_score > 0:
            notes.append("risk-signals-detected")
        if dep_edges > 0:
            notes.append("dependencies-detected")
        if any(x > 0 for x in (doc_headings, doc_bullets, doc_tables, doc_codeblocks)):
            notes.append("doc-structure-signals-present")

        return feats, notes

    def _score(self, features: Dict[str, float]) -> float:
        return sum(self.weights.get(k, 0.0) * v for k, v in features.items())

    def _map_score(self, score: float) -> str:
        t = self.thresholds
        if score < t["very_simple"]:
            return "very simple"
        if score < t["simple"]:
            return "simple"
        if score < t["medium"]:
            return "medium"
        if score < t["complex"]:
            return "complex"
        return "very complex"

    def _domain_keyword_score(self, names: List[str]) -> int:
        score = 0
        for name in names:
            for kw, w in self.keyword_weights.items():
                if not kw:
                    continue
                if kw in name or kw.lower() in name.lower():
                    score += int(w)
        return score

    def _risk_signal_score(self, descriptions: List[str], content: str) -> int:
        text = "\n".join([content] + descriptions)
        c = 0
        for kw in self.risk_keywords:
            try:
                hits = len(re.findall(re.escape(kw), text))
            except re.error:
                hits = text.count(kw)
            c += hits
        return min(c, 30) + max(0, c - 30) // 5

    def analyze_requirement_risks(self, requirement: str) -> Dict:
        """分析需求中的风险点"""
        analysis = {
            "platform_risks": [],
            "application_risks": [],
            "functional_risks": [],
            "core_feature_risks": [],
            "overall_risk": "medium"
        }

        # 处理空值或None
        if not requirement:
            return analysis

        # 获取知识库数据
        kb = get_optimization_config().get_config().get("knowledge_base", {})
        requirement_lower = requirement.lower()

        # 分析平台风险
        endpoints = kb.get("endpoints", {}).get("items", [])
        for endpoint in endpoints:
            name = endpoint.get("name", "")
            aliases = endpoint.get("aliases", [])
            if any(alias.lower() in requirement_lower for alias in [name] + aliases):
                risk = endpoint.get("risk", "medium")
                analysis["platform_risks"].append({
                    "platform": name,
                    "risk": risk,
                    "weight": self.risk_weight_map.get(risk, 4)
                })

        # 分析应用类型风险
        app_types = kb.get("application_types", {}).get("items", {})
        for category, details in app_types.items():
            if isinstance(details, dict):
                examples = details.get("examples", [])
                subtypes = details.get("subtypes", [])
                if any(example.lower() in requirement_lower for example in examples + subtypes):
                    risk = details.get("risk", "medium")
                    analysis["application_risks"].append({
                        "category": category,
                        "risk": risk,
                        "weight": self.risk_weight_map.get(risk, 4)
                    })

        # 分析功能风险
        functional_keywords = kb.get("functional_keywords", {}).get("items", [])
        for func in functional_keywords:
            name = func.get("name", "")
            en_name = func.get("en", "")
            if name.lower() in requirement_lower or en_name.lower() in requirement_lower:
                risk = func.get("risk", "medium")
                analysis["functional_risks"].append({
                    "function": name,
                    "risk": risk,
                    "weight": self.risk_weight_map.get(risk, 4)
                })

        # 分析核心功能风险
        core_features = kb.get("core_features", {}).get("groups", {})
        for group_name, group_items in core_features.items():
            for item in group_items:
                name = item.get("name", "")
                en_name = item.get("en", "")
                if name.lower() in requirement_lower or en_name.lower() in requirement_lower:
                    risk = item.get("risk", "medium")
                    analysis["core_feature_risks"].append({
                        "feature": name,
                        "group": group_name,
                        "risk": risk,
                        "weight": self.risk_weight_map.get(risk, 4)
                    })

        # 计算总体风险
        all_weights = []
        for risk_list in [analysis["platform_risks"], analysis["application_risks"], 
                         analysis["functional_risks"], analysis["core_feature_risks"]]:
            for item in risk_list:
                if isinstance(item, dict) and "weight" in item:
                    all_weights.append(item["weight"])
                else:
                    logger.warning(f"Unexpected item format in risk analysis: {item}")

        if all_weights:
            avg_weight = sum(all_weights) / len(all_weights)
            if avg_weight >= 12:
                analysis["overall_risk"] = "critical"
            elif avg_weight >= 8:
                analysis["overall_risk"] = "high"
            elif avg_weight >= 4:
                analysis["overall_risk"] = "medium"
            else:
                analysis["overall_risk"] = "low"

        return analysis

    @staticmethod
    def get_risk_based_test_types(risk_level: str) -> List[str]:
        """根据风险等级从知识库获取测试类型"""
        kb = get_optimization_config().get_config().get("knowledge_base", {})
        testing_keywords = kb.get("testing_keywords", {}).get("items", [])

        suggested_types = []
        for test_type in testing_keywords:
            test_name = test_type.get("name", "")
            test_iso = test_type.get("iso", "").lower()

            # 解析ISO标准，支持多个维度（用 / 分隔）
            iso_dimensions = [dim.strip() for dim in test_iso.split('/')]

            # 根据风险等级匹配
            if risk_level == "critical":
                if any(any(keyword in dim for keyword in ["security", "performance", "reliability", "compliance"])
                       for dim in iso_dimensions):
                    suggested_types.append(test_name)
            elif risk_level == "high":
                if any(any(keyword in dim for keyword in ["security", "performance", "functional"])
                       for dim in iso_dimensions):
                    suggested_types.append(test_name)
            elif risk_level == "medium":
                if any(any(keyword in dim for keyword in ["functional", "usability"])
                       for dim in iso_dimensions):
                    suggested_types.append(test_name)
            else:  # low
                if any("functional" in dim for dim in iso_dimensions):
                    suggested_types.append(test_name)

        # 如果没有匹配到，返回基础测试类型
        if not suggested_types:
            fallback_types = {
                "critical": ["功能测试", "性能测试", "安全测试", "合规测试"],
                "high": ["功能测试", "性能测试", "安全测试"],
                "medium": ["功能测试", "兼容性测试", "可用性测试"],
                "low": ["功能测试"]
            }
            suggested_types = fallback_types.get(risk_level, ["功能测试"])

        return list(set(suggested_types))

    @staticmethod
    def get_risk_based_test_methods(risk_level: str) -> List[str]:
        """根据风险等级从知识库获取测试方法"""
        kb = get_optimization_config().get_config().get("knowledge_base", {})
        test_methods = kb.get("test_methods", {}).get("items", [])

        suggested_methods = []
        for method in test_methods:
            method_name = method.get("name", "")
            method_iso = method.get("iso", "").lower()

            # 解析ISO标准，支持多个维度（用 / 分隔）
            iso_dimensions = [dim.strip() for dim in method_iso.split('/')]

            # 基础方法
            if any("functional" in dim for dim in iso_dimensions):
                suggested_methods.append(method_name)

            # 高风险需要更复杂的方法
            if risk_level in ["high", "critical"]:
                if any(any(keyword in dim for keyword in ["performance", "usability"])
                       for dim in iso_dimensions):
                    suggested_methods.append(method_name)

        # 如果没有匹配到，返回基础测试方法
        if not suggested_methods:
            fallback_methods = {
                "critical": ["等价类划分法", "边界值分析法", "因果图法", "判定表法", "正交分析法", "场景法", "状态迁移测试", "错误推测法"],
                "high": ["等价类划分法", "边界值分析法", "因果图法", "判定表法", "场景法", "状态迁移测试"],
                "medium": ["等价类划分法", "边界值分析法", "因果图法", "场景法"],
                "low": ["等价类划分法", "边界值分析法", "场景法"]
            }
            suggested_methods = fallback_methods.get(risk_level, ["等价类划分法", "边界值分析法"])

        return list(set(suggested_methods))

    @staticmethod
    def _dependency_metrics(names: List[str], descriptions: List[str]) -> Tuple[int, float]:
        n = len(names)
        if n <= 1:
            return 0, 0.0
        edges, degrees = 0, [0] * n
        lowered = [nm.lower() for nm in names]
        for i in range(n):
            blob_i = (names[i] + "\n" + (descriptions[i] if i < len(descriptions) else ""))
            blob_i_low = blob_i.lower()
            for j in range(n):
                if i == j or not names[j]:
                    continue
                if (names[j] in blob_i) or (lowered[j] in blob_i_low):
                    edges += 1
                    degrees[i] += 1
                    degrees[j] += 1
        max_deg = max(degrees) if degrees else 0
        centrality = (max_deg / float(max(1, n - 1)))
        return edges, min(1.0, centrality)

    @staticmethod
    def _doc_structure(content: str) -> Tuple[int, int, int, int]:
        if not content:
            return 0, 0, 0, 0
        headings = re.findall(r"^(?:#{1,6}\s+.+|\d+\.\s+.+|【.+】)\s*$", content, flags=re.MULTILINE)
        bullets = re.findall(r"^\s*[-*+]\s+[^\n]+$", content, flags=re.MULTILINE)
        tables = re.findall(r"^\s*\|.+\|\s*$|^\s*[-:]{3,}\s*\|\s*[-:]{3,}$", content, flags=re.MULTILINE)
        codeblocks = re.findall(r"```[\s\S]*?```", content)
        return len(headings), len(bullets), len(tables), len(codeblocks)


def assess_complexity(
    modules: Union[List[Dict], Dict, str],
    estimated_cases: int,
    content: str = "",
    profile: str = "balanced",
    return_details: bool = True
) -> Union[Dict, str]:
    """
    复杂度评估入口函数
    """
    # 参数兜底处理
    if isinstance(modules, str):
        modules = [{"name": modules, "description": content}]
    elif isinstance(modules, dict):
        modules = [modules]
    elif not isinstance(modules, list):
        raise TypeError(f"modules 参数必须是 list[dict] | dict | str，但传入了 {type(modules)}")

    scorer = ComplexityScorer.from_knowledge_base(profile=profile)
    res = scorer.assess(modules, estimated_cases, content=content, return_details=return_details)
    return res.to_dict() if return_details and hasattr(res, "to_dict") else res


