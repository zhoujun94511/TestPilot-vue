#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
需求分析器模块
负责从文档中提取和分析需求信息
"""
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.settings import settings
from models.models import RequirementAnalysisList
from utils.utils_core.logger import get_logger
from utils.utils_core.api_error_handler import normalize_provider_error

logger = get_logger(__name__)

def _infer_language_instruction(text: str) -> str:
    zh_count = sum(1 for ch in (text or '') if '\u4e00' <= ch <= '\u9fff')
    en_count = sum(1 for ch in (text or '') if ('a' <= ch.lower() <= 'z'))
    if zh_count > en_count:
        return "请使用简体中文输出字段内容。"
    if en_count > zh_count:
        return "Please output field contents in English."
    return "请跟随输入文本主体语言输出字段内容。"


def analyze_requirement(llm, requirement):
    """
    分析需求文本，提取结构化需求信息

    Args:
        llm: 语言模型实例
        requirement: 需求文本

    Returns:
        dict: 解析后的需求结构
    """
    try:
        # 使用Pydantic模型和JsonOutputParser
        parser = JsonOutputParser(pydantic_object=RequirementAnalysisList)
        
        # 使用自定义的简短格式说明，替代 LangChain 自动生成的长 prompt
        # 减少 token 消耗，同时保持格式要求清晰
        custom_format_instructions = """请严格按照以下JSON格式返回，不要添加任何解释文字或Markdown代码块：

{
  "requirements": [
    {
      "title": "需求标题",
      "content": "需求内容",
      "type": "functional|non-functional|business|technical",
      "priority": "P0|P1|P2|P3"
    }
  ]
}"""
        
        prompt_template = settings.REQUIREMENT_PROMPT + "\n\n语言输出要求：{language_instruction}\n"
        requirement_prompt = PromptTemplate.from_template(prompt_template).partial(
            format_instructions=custom_format_instructions,
            language_instruction=_infer_language_instruction(requirement)
        )
        chain = requirement_prompt | llm | parser
        
        # 先获取原始响应，用于调试
        try:
            result = chain.invoke({"context": requirement})
        except Exception as parse_error:
            # 如果解析失败，尝试直接调用 LLM 获取原始响应
            logger.warning(f"JSON解析失败，尝试获取原始响应: {str(parse_error)}")
            try:
                # 直接调用 LLM 获取原始文本响应
                prompt_text = requirement_prompt.format(context=requirement)
                raw_response = llm.invoke(prompt_text)
                
                # 记录原始响应
                if hasattr(raw_response, 'content'):
                    raw_content = raw_response.content
                else:
                    raw_content = str(raw_response)
                
                logger.debug(f"原始响应内容: {raw_content[:500]}...")  # 只记录前500字符
                logger.error(f"JSON解析失败，原始响应: {raw_content}", exc_info=True)
                
                # 尝试手动解析 JSON（优先解析 ```json 代码块，避免贪婪匹配误伤）
                import json
                import re
                json_str = None
                fence_match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_content, re.IGNORECASE)
                if fence_match:
                    json_str = fence_match.group(1)
                else:
                    start = raw_content.find('{')
                    end = raw_content.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_str = raw_content[start:end + 1]

                if json_str:
                    try:
                        parsed_json = json.loads(json_str)
                        if isinstance(parsed_json, dict) and 'requirements' in parsed_json:
                            logger.info(f"手动解析成功，需求数量: {len(parsed_json['requirements'])}")
                            return parsed_json['requirements']
                    except json.JSONDecodeError as json_err:
                        logger.error(f"手动JSON解析也失败: {str(json_err)}")
                
                return []
            except Exception as llm_error:
                normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), llm_error)
                logger.error(f"获取原始响应失败: {normalized.get('message')}", exc_info=True)
                raise RuntimeError(normalized.get('message', '需求分析模型调用失败')) from llm_error
        
        # 返回需求列表
        if isinstance(result, dict) and 'requirements' in result:
            return result['requirements']
        elif hasattr(result, 'requirements'):
            return result.requirements
        elif isinstance(result, list):
            return result
        else:
            logger.warning(f"未知结果类型: {type(result)}, 内容: {result}")
            return []
            
    except Exception as e:
        normalized = normalize_provider_error(getattr(settings, 'DEFAULT_COMPANY', 'OPENAI'), e)
        logger.error(f"解析需求失败: {normalized.get('message')}", exc_info=True)
        raise RuntimeError(normalized.get('message', '解析需求失败')) from e


def extract_requirements_from_text(text: str, llm=None) -> list:
    """
    从文本中提取多个需求

    Args:
        text: 输入文本
        llm: 语言模型实例

    Returns:
        list: 需求列表
    """
    try:
        if not text or not llm:
            return []

        # 分段处理长文本
        paragraphs = text.split('\n\n')
        requirements = []

        for paragraph in paragraphs:
            if len(paragraph.strip()) > 50:  # 过滤太短的段落
                req = analyze_requirement(llm, paragraph)
                if req:
                    requirements.append(req)

        return requirements
    except Exception as e:
        logger.error(f"批量提取需求失败: {str(e)}")
        return []


def validate_requirement(requirement: dict) -> bool:
    """
    验证需求结构的完整性

    Args:
        requirement: 需求字典

    Returns:
        bool: 验证结果
    """
    try:
        required_fields = ['title', 'content', 'type', 'priority']
        return all(field in requirement and requirement[field] for field in required_fields)
    except Exception as e:
        logger.error(f"需求验证失败: {str(e)}")
        return False