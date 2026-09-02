// 추론 서비스 호출 — 실패해도 진단 흐름이 무너지지 않아야 한다 (설계 4.9.4).
//   전송 층(Transport)을 주입해 시험한다. 실제 통신은 유닉스 소켓이라 포트를 쓰지 않는다.
import { describe, it, expect, vi } from 'vitest';
import { callInference, inferenceHealth, type Transport } from '../../src/services/inferenceClient.js';

const REQ = {
  answers: [{ questionNo: 1, value: 4 }],
  policy: { tauConf: 0.3, tauDens: -2.4, decisionWeights: [1.1, 1.1, 1, 1, 1],
            contributionMinThreshold: 0.13 },
};

const OK = {
  modelVersion: 'v1.0.0', questionSetVersion: 'qs-v1.0.0',
  proba: [0.1, 0.2, 0.3, 0.3, 0.1], decided: true, internalLabel: 3,
  maxProba: 0.3, rarity: -1.1, undecidableReason: null, contributions: [],
};

const ok: Transport = async () => ({ status: 200, json: OK });

describe('추론 서비스 호출', () => {
  it('정상 응답을 그대로 돌려준다', async () => {
    const r = await callInference(REQ, ok);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.internalLabel).toBe(3);
  });

  it('5xx 면 unavailable 이다', async () => {
    const r = await callInference(REQ, async () => ({ status: 500, json: null }));
    expect(r.ok).toBe(false);
  });

  it('소켓 연결 실패면 unavailable 이다 — 예외를 던지지 않는다', async () => {
    const r = await callInference(REQ, async () => { throw new Error('ENOENT socket'); });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toContain('ENOENT');
  });

  it('한 번 재시도한다', async () => {
    const t = vi.fn<Transport>()
      .mockRejectedValueOnce(new Error('ENOENT'))
      .mockResolvedValueOnce({ status: 200, json: OK });
    const r = await callInference(REQ, t);
    expect(r.ok).toBe(true);
    expect(t).toHaveBeenCalledTimes(2);
  });

  it('두 번 다 실패하면 포기한다 — 무한 재시도하지 않는다', async () => {
    const t = vi.fn<Transport>(async () => { throw new Error('ENOENT'); });
    const r = await callInference(REQ, t);
    expect(r.ok).toBe(false);
    expect(t).toHaveBeenCalledTimes(2);
  });

  it('응답 모양이 계약과 다르면 unavailable 이다', async () => {
    // 필드 이름이 어긋난 채 통과하면 2026-09-02 오전 사고가 반복된다
    const r = await callInference(REQ, async () => ({ status: 200, json: { hello: 'world' } }));
    expect(r.ok).toBe(false);
  });

  it('predict 경로로 POST 한다', async () => {
    const t = vi.fn<Transport>(async () => ({ status: 200, json: OK }));
    await callInference(REQ, t);
    expect(t).toHaveBeenCalledWith('POST', '/predict', REQ);
  });
});

describe('기동 시 상태 확인', () => {
  it('버전과 가중치를 돌려준다', async () => {
    const got = await inferenceHealth(async () => ({
      status: 200,
      json: { modelVersion: 'v1.0.0', questionSetVersion: 'qs-v1.0.0',
              artifactDecisionWeights: [1.1, 1.1, 1, 1, 1] },
    }));
    expect(got?.questionSetVersion).toBe('qs-v1.0.0');
  });

  it('못 붙으면 null 이다 — 서버는 뜬다', async () => {
    const got = await inferenceHealth(async () => { throw new Error('ENOENT'); });
    expect(got).toBeNull();
  });
});
