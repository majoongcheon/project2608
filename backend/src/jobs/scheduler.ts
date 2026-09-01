// 보존 기간 파기와 솔트 교체 (FR-030·FR-035·FR-037)
//   컨테이너를 쓰지 않는다(원칙 V). Node 프로세스 안의 타이머로 돌리고 이력을 남긴다.
import crypto from 'node:crypto';
import { exec, query } from '../repositories/pool.js';

const DAY_MS = 24 * 60 * 60 * 1000;

async function record(job: string, fn: () => Promise<number>) {
  const res = await exec(
    "INSERT INTO cb_job_run_v1 (job_name, started_at, status) VALUES (?, NOW(), 'RUNNING')", [job]);
  try {
    const n = await fn();
    await exec(
      "UPDATE cb_job_run_v1 SET finished_at = NOW(), affected = ?, status = 'OK' WHERE job_run_id = ?",
      [n, res.insertId]);
    if (n > 0) console.log(`[job] ${job}: ${n}건 처리`);
  } catch (e: any) {
    await exec(
      "UPDATE cb_job_run_v1 SET finished_at = NOW(), status = 'FAILED', detail = ? WHERE job_run_id = ?",
      [String(e?.message ?? e).slice(0, 500), res.insertId]);
    console.error(`[job] ${job} 실패:`, e?.message ?? e);
  }
}

/** 익명 집계 로그 12개월 (FR-030) */
async function purgeEvents(): Promise<number> {
  const r = await exec(
    'DELETE FROM cb_event_log_v1 WHERE occurred_at < (NOW() - INTERVAL 12 MONTH)');
  return r.affectedRows ?? 0;
}

/** 학습용 응답 36개월 (FR-035) */
async function purgeTraining(): Promise<number> {
  const r = await exec(
    'DELETE FROM cb_training_response_v1 WHERE submitted_at < (NOW() - INTERVAL 36 MONTH)');
  return r.affectedRows ?? 0;
}

/** 취소 창이 닫힌 토큰 폐기 — 이후에는 삭제권이 성립하지 않는다(FR-025) */
async function expireCancelTokens(): Promise<number> {
  const r = await exec(
    'UPDATE cb_training_response_v1 SET cancel_token = NULL ' +
    'WHERE cancel_token IS NOT NULL AND submitted_at < (NOW() - INTERVAL 2 HOUR)');
  return r.affectedRows ?? 0;
}

/** 분기 1회 솔트 교체 (FR-037) */
async function rotateSalt(): Promise<number> {
  const rows = await query<{ n: number }>(
    'SELECT COUNT(*) n FROM cb_salt_v1 WHERE active_to IS NULL AND active_from > (NOW() - INTERVAL 90 DAY)');
  if (Number(rows[0]?.n ?? 0) > 0) return 0;
  await exec('UPDATE cb_salt_v1 SET active_to = NOW() WHERE active_to IS NULL');
  await exec('INSERT INTO cb_salt_v1 (salt_value) VALUES (?)', [crypto.randomBytes(32)]);
  return 1;
}

export function startJobs() {
  const run = () => {
    void record('purge_events', purgeEvents);
    void record('purge_training', purgeTraining);
    void record('expire_cancel_tokens', expireCancelTokens);
    void record('rotate_salt', rotateSalt);
  };
  setTimeout(run, 10_000).unref();
  setInterval(run, DAY_MS).unref();
}
