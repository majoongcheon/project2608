// 익명 집계 로그 (FR-027~FR-030)
//   ★ FR-027 이 열거한 종류와 필드만 저장하고 나머지는 조용히 버린다.
//   ★ IP·별명·문항 응답·사전 입력값·좌표는 컬럼 자체가 없어 저장할 수 없다(FR-028).
import { exec } from '../repositories/pool.js';

export const EVENT_TYPES = [
  'PRESURVEY_ENTER', 'PRESURVEY_PASS', 'SURVEY_START', 'QUESTION_MOVE',
  'SURVEY_COMPLETE', 'SURVEY_ABANDON', 'RESULT_SHOWN', 'MAP_ENTER',
  'FACILITY_DETAIL', 'CONTACT_ACTION',
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

export interface IncomingEvent {
  eventType: string;
  occurredAt?: string;
  questionNo?: number | null;
  durationMs?: number | null;
  regionCode?: string | null;
  modelVersion?: string | null;
  burdenLevel?: number | null;
  isUndecidable?: boolean | null;
  consentTraining?: boolean | null;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function recordEvents(sessionId: string, events: IncomingEvent[]): Promise<number> {
  if (!UUID.test(sessionId)) return 0;               // 1회용 난수만 받는다(FR-029)
  const rows = events
    .filter((e) => (EVENT_TYPES as readonly string[]).includes(e.eventType))
    .slice(0, 100)
    .map((e) => [
      sessionId,
      e.eventType,
      e.occurredAt ? new Date(e.occurredAt) : new Date(),
      e.questionNo ?? null,
      e.durationMs ?? null,
      e.modelVersion ?? null,
      e.regionCode ?? null,                          // 시군구 단위까지만
      e.burdenLevel ?? null,
      e.isUndecidable == null ? null : (e.isUndecidable ? 1 : 0),
      e.consentTraining == null ? null : (e.consentTraining ? 1 : 0),
    ]);
  if (!rows.length) return 0;
  await exec(
    `INSERT INTO cb_event_log_v1
       (session_id, event_type, occurred_at, question_no, duration_ms,
        model_version, region_code, burden_level, is_undecidable, consent_training)
     VALUES ?`, [rows]);
  return rows.length;
}
