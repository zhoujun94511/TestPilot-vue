#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


def safe_json_loads(s: str):
    """
    尝试解析 LLM 返回的 JSON，容错处理常见格式错误
    """
    if not s or not isinstance(s, str):
        return {"status": "error", "message": "输出为空或非字符串", "raw": s}

    # 去掉可能的 ```json ``` 包裹
    s = s.strip().replace("```json", "").replace("```", "")

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON 解析失败: {e}，尝试修复 → {s[:200]}...")

        fixed = s

        # 修复1：尾逗号
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)

        # 修复2：未闭合的字符串
        fixed = re.sub(r'"([^"]*?)\s*$', r'"\1"', fixed)

        # 修复3：截断的JSON - 找到最后一个完整的测试用例
        if not fixed.strip().endswith("}") and not fixed.strip().endswith("]"):
            logger.warning("⚠️ JSON 未闭合，尝试补齐")
            # 找到最后一个完整的测试用例
            last_complete_case = fixed.rfind('},')
            if last_complete_case != -1:
                fixed = fixed[:last_complete_case + 1] + "\n    ]\n}"
            else:
                # 如果连一个完整用例都没有，尝试补齐
                if '"cases":' in fixed and '[' in fixed:
                    fixed = fixed.rstrip() + '] }'
                else:
                    fixed = fixed.rstrip() + "}"

        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e2:
            logger.error(f"❌ 二次修复失败: {e2}")
            # 最后尝试：截断到最后一个完整大括号
            last_brace = fixed.rfind("}")
            if last_brace != -1:
                try:
                    return json.loads(fixed[:last_brace + 1])
                except json.JSONDecodeError as e3:
                    logger.error(f"❌ 截断修复仍失败: {e3}")
            return {"status": "error", "message": "JSON 解析失败", "raw": s}