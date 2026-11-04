"""智能检索 score_threshold 与聊天 RAG 注入行为。"""
from utils.utils_intelligent_retrieval.smart_retrieval_strategy import (
    RetrievalConfig,
    RetrievalResult,
    RetrievalStrategy,
    SmartRetrievalStrategy,
)


def test_apply_score_threshold_drops_low_scores():
    strategy = SmartRetrievalStrategy(RetrievalConfig(score_threshold=0.7, top_k=5))
    results = [
        RetrievalResult("a", 0.85, {}, RetrievalStrategy.SEMANTIC, {}),
        RetrievalResult("b", 0.69, {}, RetrievalStrategy.SEMANTIC, {}),
        RetrievalResult("c", 0.71, {}, RetrievalStrategy.SEMANTIC, {}),
    ]
    kept = strategy._apply_score_threshold(results)
    assert len(kept) == 2
    assert kept[0].content == "a"
    assert kept[1].content == "c"
