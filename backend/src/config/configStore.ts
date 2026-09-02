// cb_config_v1 로더 (FR-022 · 원칙 IV)
//   판정과 연계에 영향을 주는 값은 코드에 고정하지 않는다.
//   기동 시 필수 키가 하나라도 없으면 서버를 띄우지 않는다 (fail fast).
import { query } from '../repositories/pool.js';

const REQUIRED = [
  'referral.threshold', 'referral.counselingThreshold', 'referral.facilityCount',
  'referral.radiusStepsKm', 'age.mappingBoundary', 'age.serviceRanges',
  'age.outOfRangeNotice', 'undecidable.thresholds', 'undecidable.noticeText',
  'contribution.minThreshold', 'selfreport.noticeText', 'burden.labels',
  'draft.expiryHours', 'submit.rateLimit', 'notice.disclaimer',
  'notice.modelChange', 'notice.cancelWindow', 'notice.multipleTargets',
  'model.decisionWeights', 'notice.inferenceUnavailable',
] as const;

let cache: Record<string, any> = {};

export async function loadConfig(): Promise<void> {
  const rows = await query<{ config_key: string; value_json: string }>(
    'SELECT config_key, value_json FROM cb_config_v1 WHERE version = ?', ['v1']);
  const next: Record<string, any> = {};
  for (const r of rows) next[r.config_key] = JSON.parse(r.value_json);

  const missing = REQUIRED.filter((k) => !(k in next));
  if (missing.length) {
    throw new Error(
      `cb_config_v1 에 필수 설정이 없습니다: ${missing.join(', ')}\n` +
      `  → db 폴더에서 'npm run seed:config' 를 실행하세요.`);
  }
  cache = next;
}

export function cfg<T = any>(key: string): T {
  if (!(key in cache)) throw new Error(`설정 키가 없습니다: ${key}`);
  return cache[key] as T;
}

export function allConfig(): Record<string, any> {
  return cache;
}
