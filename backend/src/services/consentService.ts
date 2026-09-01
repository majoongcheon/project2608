// 학습용 저장 분기 (FR-031·FR-033·FR-025·FR-036)
//   ★ 동의하지 않은 제출은 cb_training_response_v1 에 어떤 행도 만들지 않는다.
//   ★ 원본 IP 는 해시 생성 시점에만 메모리에서 쓰고 어디에도 저장·로깅하지 않는다.
import crypto from 'node:crypto';
import { env } from '../config/env.js';
import { query, exec, one } from '../repositories/pool.js';
import { cfg } from '../config/configStore.js';

async function activeSalt(): Promise<{ id: number; value: Buffer }> {
  const row = await one<{ salt_id: number; salt_value: Buffer }>(
    'SELECT salt_id, salt_value FROM cb_salt_v1 WHERE active_to IS NULL ORDER BY salt_id DESC LIMIT 1');
  if (row) return { id: row.salt_id, value: row.salt_value };
  const value = Buffer.from(env.submitterSalt, 'utf8');
  const res = await exec('INSERT INTO cb_salt_v1 (salt_value) VALUES (?)', [value]);
  return { id: res.insertId, value };
}

/** SHA-256(IP + 솔트). 원본 IP 는 반환값에 남지 않는다(FR-036·FR-036b). */
export async function submitterHash(ip: string | undefined) {
  const salt = await activeSalt();
  const h = crypto.createHash('sha256').update(String(ip ?? '')).update(salt.value).digest();
  return { hash: h, saltId: salt.id };
}

/** 중복 제출 탐지 — 자동 차단하지 않고 참고 플래그만 낸다(FR-036a·FR-036c). */
export async function recentSubmissionCount(hash: Buffer): Promise<number> {
  const { windowMinutes } = cfg<{ windowMinutes: number }>('submit.rateLimit');
  const rows = await query<{ n: number }>(
    `SELECT COUNT(*) n FROM cb_training_response_v1
      WHERE submitter_hash = ? AND submitted_at >= (NOW() - INTERVAL ? MINUTE)`,
    [hash, windowMinutes]);
  return Number(rows[0]?.n ?? 0);
}

export interface StoreParams {
  questionSetVersion: string;
  answers: { questionNo: number; value: number | null }[];
  selfReportLevel: number | null;
  surveyDurationSec: number | null;
  predictedLevel: number | null;
  modelVersion: string;
  ip: string | undefined;
}

/** 동의한 제출만 저장한다. 취소 토큰을 돌려준다(FR-025). */
export async function storeTrainingResponse(p: StoreParams): Promise<string> {
  const { hash, saltId } = await submitterHash(p.ip);
  const token = crypto.randomUUID();
  await exec(
    `INSERT INTO cb_training_response_v1
       (cancel_token, question_set_version, answers_json, self_report_label,
        submitted_at, survey_duration_sec, predicted_level, model_version, submitter_hash, salt_id)
     VALUES (?, ?, ?, ?, DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s'), ?, ?, ?, ?, ?)`,
    [token, p.questionSetVersion, JSON.stringify(p.answers), p.selfReportLevel,
     p.surveyDurationSec, p.predictedLevel, p.modelVersion, hash, saltId]);
  return token;
}

/** 취소 창 안에서의 삭제 (FR-025). 존재 여부를 호출자에게 알리지 않는다. */
export async function cancelTrainingResponse(token: string): Promise<void> {
  await exec('DELETE FROM cb_training_response_v1 WHERE cancel_token = ?', [token]);
}
