from services.rag_threshold_utils import search_documents_above_threshold


class _FakeDoc:
    def __init__(self, text: str):
        self.page_content = text
        self.metadata = {}


class _FakeVectorDb:
    @staticmethod
    def similarity_search_with_score(_query, k=4, **_kwargs):
        return [
            (_FakeDoc("high"), 0.82),
            (_FakeDoc("low"), 0.55),
        ][:k]


def test_search_documents_above_threshold(monkeypatch):
    from config.settings import settings

    monkeypatch.setattr(settings, "AUTH_REQUIRE_AUTH", False)
    docs = search_documents_above_threshold(_FakeVectorDb(), "q", k=5, threshold=0.7)
    assert len(docs) == 1
    assert docs[0].page_content == "high"
    assert docs[0].metadata["similarity_score"] == 0.82
