// 파이썬 추론 서비스 호출 (설계 4.9)
//   ★ 포트를 쓰지 않는다. 팀에 배정된 포트가 프론트·백엔드 둘뿐이라 유닉스 소켓(파일)으로
//     통신한다. 네트워크에 열리지 않아 외부에서 닿을 수 없다.
//   ★ 예외를 던지지 않는다. 실패는 값으로 돌려준다 — 파이썬이 죽어도 기관 안내는
//     계속 나가야 하기 때문이다(FR-021j 안전망과 같은 취지).
//   ★ 응답 모양도 검사한다. 필드 이름이 어긋난 채 통과하면 2026-09-02 오전처럼
//     아무 오류 없이 화면이 비는 사고가 난다.
import http from 'node:http';
import { env } from '../config/env.js';

export interface InferenceRequest {
  answers: { questionNo: number; value: number | null }[];
  policy: {
    tauConf: number;
    tauDens: number;
    decisionWeights: number[];
    contributionMinThreshold: number;
  };
}

export interface InferenceContribution {
  feature: string;
  value: number;
  contrib: number;
  isMinor: boolean;
}

export interface InferenceResult {
  modelVersion: string;
  questionSetVersion: string;
  proba: number[];
  decided: boolean;
  internalLabel: number | null;
  maxProba: number;
  rarity: number;
  undecidableReason: 'sparse' | 'ambiguous' | null;
  contributions: InferenceContribution[] | null;
}

export type InferenceOutcome =
  | { ok: true; value: InferenceResult }
  | { ok: false; reason: string };

/** 소켓 통신 층. 테스트에서는 가짜를 넣는다. */
export type Transport = (
  method: 'GET' | 'POST', path: string, body?: unknown,
) => Promise<{ status: number; json: any }>;

/** 기본 전송 — 유닉스 소켓 위의 HTTP. 포트를 열지 않는다. */
export const socketTransport: Transport = (method, path, body) =>
  new Promise((resolve, reject) => {
    const payload = body === undefined ? undefined : JSON.stringify(body);
    const req = http.request(
      {
        socketPath: env.inferenceSocket,
        path,
        method,
        timeout: env.inferenceTimeoutMs,
        headers: payload
          ? { 'content-type': 'application/json',
              'content-length': String(Buffer.byteLength(payload)) }
          : {},
      },
      (res) => {
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (c) => { data += c; });
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode ?? 0, json: data ? JSON.parse(data) : null });
          } catch {
            reject(new Error('추론 서비스 응답이 JSON 이 아닙니다'));
          }
        });
      },
    );
    req.on('timeout', () => req.destroy(
      new Error(`추론 서비스가 ${env.inferenceTimeoutMs}ms 안에 답하지 않았습니다`)));
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });

/** 계약대로 생긴 응답인지. 하나라도 어긋나면 쓰지 않는다. */
function isResult(v: any): v is InferenceResult {
  return v
    && typeof v.modelVersion === 'string'
    && typeof v.questionSetVersion === 'string'
    && Array.isArray(v.proba) && v.proba.length === 5
    && typeof v.decided === 'boolean'
    && (v.internalLabel === null || typeof v.internalLabel === 'number')
    && typeof v.maxProba === 'number'
    && typeof v.rarity === 'number'
    && (v.undecidableReason === null
        || v.undecidableReason === 'sparse' || v.undecidableReason === 'ambiguous')
    && (v.contributions === null || Array.isArray(v.contributions));
}

async function once(req: InferenceRequest, send: Transport): Promise<InferenceResult> {
  const res = await send('POST', '/predict', req);
  if (res.status !== 200) throw new Error(`추론 서비스가 ${res.status} 를 냈습니다`);
  if (!isResult(res.json)) throw new Error('추론 서비스 응답이 계약과 다릅니다');
  return res.json;
}

/** 실패해도 던지지 않는다. 호출자가 안내 화면을 만든다. */
export async function callInference(
  req: InferenceRequest, send: Transport = socketTransport,
): Promise<InferenceOutcome> {
  let last = '';
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      return { ok: true, value: await once(req, send) };
    } catch (e: any) {
      last = String(e?.message ?? e);
    }
  }
  console.error('[inference] 호출 실패:', last);
  return { ok: false, reason: last };
}

export interface InferenceHealth {
  modelVersion: string;
  questionSetVersion: string;
  artifactDecisionWeights: number[];
}

/** 기동 시 버전 대조용. 못 붙으면 null — 진단만 불가하고 서버는 뜬다. */
export async function inferenceHealth(
  send: Transport = socketTransport,
): Promise<InferenceHealth | null> {
  try {
    const res = await send('GET', '/health');
    if (res.status !== 200) return null;
    const b = res.json;
    if (typeof b?.modelVersion !== 'string' || typeof b?.questionSetVersion !== 'string') {
      return null;
    }
    return b as InferenceHealth;
  } catch {
    return null;
  }
}
