/** 批量生成：多条需求的分隔符约定（仅前端 textarea → API requirements[]） */
export const BATCH_REQUIREMENT_DELIMITER = ';';

const BATCH_REQUIREMENT_SPLIT_PATTERN = /[;；]+/;

/**
 * 将批量需求文本拆成字符串数组。
 * 约定：条目之间用英文 `;` 或中文 `；` 分隔，末尾分号可选。
 */
export function parseBatchRequirementText(text: string): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  return trimmed
    .split(BATCH_REQUIREMENT_SPLIT_PATTERN)
    .map((segment) => segment.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}
