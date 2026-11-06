"""单个需求生成用例的数量。界面可选，这里卡住上限。"""
MAX_CASES_PER_REQUIREMENT = 10


def clamp_cases_per_requirement(value, default: int = 5) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = default
    if count < 1:
        return 1
    if count > MAX_CASES_PER_REQUIREMENT:
        return MAX_CASES_PER_REQUIREMENT
    return count
