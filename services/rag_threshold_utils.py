"""RAG 向量检索与 score_threshold 对齐（聊天、幻觉检测、知识库传统检索等共用）。"""
from __future__ import annotations

from typing import Any, List, Optional

from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def get_rag_score_threshold() -> float:
    """配置中心 > settings > 默认 0.7。"""
    from config.settings import settings

    default = float(getattr(settings, "RAG_SCORE_THRESHOLD", 0.7))
    try:
        from services.config_center_service import config_center_service

        return float(
            config_center_service.get_config_value("RAG_SCORE_THRESHOLD", default)
        )
    except Exception:
        return default


def search_documents_above_threshold(
    vector_db: Any,
    query: str,
    k: int,
    threshold: Optional[float] = None,
    *,
    apply_scope_kwargs: bool = True,
) -> List[Any]:
    """
    带分数检索，仅返回 similarity >= threshold 的 Document。
    metadata 中会写入 similarity_score。
    """
    text = str(query or "").strip()
    if not text or not vector_db or k <= 0:
        return []

    cutoff = float(threshold if threshold is not None else get_rag_score_threshold())
    kwargs = {}
    if apply_scope_kwargs:
        try:
            from services.knowledge_vector_scope import merged_vector_search_kwargs

            kwargs = merged_vector_search_kwargs()
        except Exception:
            kwargs = {}

    pairs: List[tuple] = []
    try:
        pairs = list(
            vector_db.similarity_search_with_score(text, k=k, **kwargs)
        )
    except Exception as exc:
        logger.debug("similarity_search_with_score 失败，无法按阈值过滤: %s", exc)
        return []

    kept: List[Any] = []
    for doc, score in pairs:
        sim = float(score or 0)
        if sim < cutoff:
            continue
        meta = dict(getattr(doc, "metadata", None) or {})
        meta["similarity_score"] = sim
        try:
            doc.metadata = meta
        except Exception:
            pass
        kept.append(doc)
    if apply_scope_kwargs:
        from services.data_scope import filter_scoped_retrieval_items

        kept = filter_scoped_retrieval_items(kept)
    if pairs and not kept:
        logger.debug(
            "RAG 检索 %d 条均未达 threshold=%.3f，query=%r",
            len(pairs),
            cutoff,
            text[:80],
        )
    return kept
