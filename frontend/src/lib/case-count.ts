/** 与 services/case_count.py 的上限一致：一个需求最多生成 10 条用例。 */
export const MAX_CASES_PER_REQUIREMENT = 10;

export const CASE_COUNT_CHOICES = [1, 2, 3, 5, 8, 10] as const;

export function clampCaseCount(value: unknown, fallback = 5): number {
  const parsed = Number(value);
  const count = Number.isFinite(parsed) ? Math.trunc(parsed) : fallback;
  return Math.min(MAX_CASES_PER_REQUIREMENT, Math.max(1, count));
}
