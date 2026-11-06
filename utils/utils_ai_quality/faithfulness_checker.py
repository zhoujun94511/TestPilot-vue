#!/usr/bin/env python3
"""对照原文检查带单位的数量，区分能推出、互相矛盾和原文没写。"""

import re
from typing import Any, Dict, List, Optional

_UNIT = r"%|％|天|小时|分钟|秒|次|个|位|元|条|字符|字"
_QUANTIFIED = re.compile(
    rf"(?:不超过|不少于|至少|至多|最多|大于|小于|超过|低于|等于|约)?\s*"
    rf"(\d+(?:\.\d+)?)\s*"
    rf"({_UNIT})"
)
_RANGE = re.compile(
    rf"(\d+(?:\.\d+)?)\s*[到至\-~～]\s*(\d+(?:\.\d+)?)\s*({_UNIT})"
)
_EXPLORATORY = re.compile(r"边界|负向|负面|异常|反例|boundary|negative|exception|invalid", re.IGNORECASE)


def case_allows_unmentioned(case: Dict[str, Any]) -> bool:
    """边界、负向和异常用例允许写出原文里没有的数量。"""
    if not isinstance(case, dict):
        return False
    parts = []
    for key in ("category", "test_type", "test_method", "title", "tags"):
        value = case.get(key)
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value))
        elif value is not None:
            parts.append(str(value))
    return bool(_EXPLORATORY.search(" ".join(parts)))


def join_source_text(source_documents: Optional[List[Dict[str, Any]]] = None, context: str = None) -> str:
    parts = []
    if context:
        parts.append(str(context))
    for doc in source_documents or []:
        if not isinstance(doc, dict):
            continue
        text = doc.get("content") or doc.get("page_content") or ""
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def assess_quantified_claims(content: str, source_text: str, allow_unmentioned: bool = False) -> List[Dict[str, str]]:
    """只检查带单位的数量。没有单位的数字当作测试数据，不参与拦截。"""
    claims = []
    seen = set()
    for match in _QUANTIFIED.finditer(content or ""):
        number = match.group(1)
        unit = match.group(2)
        key = (number, unit, match.start())
        if key in seen:
            continue
        seen.add(key)
        sentence = _sentence_at(content, match.start())
        verdict, reason = _quantity_verdict(number, unit, source_text, allow_unmentioned)
        claims.append({
            "text": sentence,
            "number": number,
            "unit": unit,
            "verdict": verdict,
            "reason": reason,
        })
    return claims


def contradiction_issue(claim: Dict[str, str]) -> str:
    quantity = f"{claim.get('number', '')}{claim.get('unit', '')}"
    sentence = claim.get("text", "")
    if claim.get("reason") == "unit_mismatch":
        return f"互相矛盾: 「{sentence}」中的 {quantity} 与原文单位不一致"
    return f"互相矛盾: 「{sentence}」中的 {quantity} 在原文中没有出现"


def source_quantity_pairs(source_text: str) -> set:
    pairs = set()
    for match in _QUANTIFIED.finditer(source_text or ""):
        pairs.add((match.group(1), match.group(2)))
    for match in _RANGE.finditer(source_text or ""):
        pairs.add((match.group(1), match.group(3)))
        pairs.add((match.group(2), match.group(3)))
    return pairs


def _quantity_verdict(number: str, unit: str, source_text: str, allow_unmentioned: bool):
    pairs = source_quantity_pairs(source_text)
    if (number, unit) in pairs:
        return "entailed", ""
    if any(item_number == number and item_unit != unit for item_number, item_unit in pairs):
        return "contradicted", "unit_mismatch"
    if allow_unmentioned or not (source_text or "").strip():
        return "not_mentioned", ""
    return "contradicted", "absent"


def expected_sentences(value: Any, limit: int = 4) -> List[str]:
    """抽出预期结果里不含数量单位的短句，交给模型逐句判断。"""
    if isinstance(value, list):
        raw = "。".join(str(item) for item in value if item)
    else:
        raw = str(value or "")
    sentences = []
    for part in re.split(r"[。；;\n]+", raw):
        text = part.strip()
        if len(text) < 4 or _QUANTIFIED.search(text):
            continue
        sentences.append(text)
        if len(sentences) >= limit:
            break
    return sentences


def judge_sentences(llm, source_text: str, sentences: List[str]) -> List[Dict[str, str]]:
    """一次判断同一条用例里的短句。模型不可用时不拦截。"""
    if llm is None or not sentences or not (source_text or "").strip():
        return []
    numbered = "\n".join(f"{index}. {text}" for index, text in enumerate(sentences, start=1))
    prompt = (
        "逐句对照原文。verdict 只能是 entailed、contradicted、not_mentioned。"
        "和原文相反才标 contradicted。原文没写的操作标 not_mentioned。\n"
        f"原文：\n{source_text[:2000]}\n"
        f"句子：\n{numbered}\n"
        '只返回 JSON 数组，例如 [{"index":1,"verdict":"entailed"}]。'
    )
    from utils.utils_performance_monitoring.token_monitor import ensure_session_budget, record_message_usage
    from utils.utils_performance_monitoring.token_session import TokenSessionLimitExceeded

    try:
        ensure_session_budget()
        response = llm.invoke([{"role": "user", "content": prompt}])
        record_message_usage(response, source="case_generation")
        content = response.content if hasattr(response, "content") else str(response)
    except (TokenSessionLimitExceeded, AttributeError, TypeError, ValueError, RuntimeError, OSError, TimeoutError):
        return []
    return _parse_sentence_verdicts(content, sentences)


def _parse_sentence_verdicts(content: str, sentences: List[str]) -> List[Dict[str, str]]:
    import json
    match = re.search(r"\[[\s\S]*]", content or "")
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    allowed = {"entailed", "contradicted", "not_mentioned"}
    verdicts = []
    if not isinstance(payload, list):
        return []
    for item in payload:
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict") or "")
        if verdict not in allowed:
            continue
        index = item.get("index")
        try:
            position = int(index) - 1
        except (TypeError, ValueError):
            continue
        if position < 0 or position >= len(sentences):
            continue
        verdicts.append({"text": sentences[position], "verdict": verdict, "reason": "sentence"})
    return verdicts


def _sentence_at(content: str, index: int) -> str:
    start = max(content.rfind("\n", 0, index), content.rfind("。", 0, index), content.rfind("；", 0, index))
    end_candidates = [pos for pos in (content.find("\n", index), content.find("。", index), content.find("；", index)) if pos >= 0]
    end = min(end_candidates) if end_candidates else len(content)
    return content[start + 1:end].strip() or content[max(0, index - 12):index + 12].strip()
