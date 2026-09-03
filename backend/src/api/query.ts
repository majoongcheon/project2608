import { ApiError } from '../middleware/errors.js';

/**
 * 주소창에서 온 숫자 읽기 (2026-09-03)
 *
 * `Math.min(Number(q.limit ?? 20), 100)` 처럼 쓰면 `limit=abc` 는 NaN,
 * `limit=-5` 는 음수가 그대로 SQL 로 내려가 **500 이 난다**. 실제로 두 곳이
 * 그랬다 — `/reviews` 와 `/facilities`. 주소는 누구나 손으로 고칠 수 있으니
 * 이상한 값이 와도 500 이 아니라 **말이 되는 값이나 400** 이어야 한다.
 */
export function intParam(
  raw: unknown,
  { def, min, max, name }: { def: number; min: number; max: number; name: string },
): number {
  if (raw === undefined || raw === null || raw === '') return def;
  const n = Number(raw);
  if (!Number.isFinite(n)) {
    throw new ApiError(400, 'BAD_QUERY', `${name} 값이 올바르지 않습니다.`);
  }
  return Math.min(Math.max(Math.trunc(n), min), max);
}

/** 위도·경도. 범위를 벗어나면 좌표가 아니다 */
export function coordParam(raw: unknown, kind: 'lat' | 'lng'): number | null {
  if (raw === undefined || raw === null || raw === '') return null;
  const n = Number(raw);
  const limit = kind === 'lat' ? 90 : 180;
  if (!Number.isFinite(n) || Math.abs(n) > limit) {
    throw new ApiError(400, 'BAD_COORD', '위치 값이 올바르지 않습니다.');
  }
  return n;
}
