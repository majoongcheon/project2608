// 추론 서비스가 죽었을 때 — 진단은 못 하지만 기관 안내는 나가야 한다 (설계 4.9.4)
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../src/services/inferenceClient.js', () => ({
  callInference: async () => ({ ok: false, reason: 'ECONNREFUSED' }),
  inferenceHealth: async () => null,
}));
vi.mock('../../src/config/env.js', () => ({
  env: { inferenceMode: 'http', inferenceUrl: 'http://x', inferenceTimeoutMs: 100 },
}));
vi.mock('../../src/inference/modelLoader.js', () => ({
  getArtifacts: () => ({
    questions: { questions: [{ questionNo: 1, feature: 'a' }] },
    model: { question_set_version: 'qs-v1.0.0', model_version: 'v1.0.0',
             features: ['a'], classes: [1, 2, 3, 4, 5], missing_sentinel: -1 },
    uncertainty: { tau_conf: 0.3, tau_dens: -2.4, freq_table: {} },
    contributionThreshold: 0.13,
  }),
}));
vi.mock('../../src/config/configStore.js', () => ({
  cfg: (k: string) => ({
    'undecidable.thresholds': { tauConf: 0.3, tauDens: -2.4 },
    'model.decisionWeights': { weights: [1.1, 1.1, 1, 1, 1] },
    'contribution.minThreshold': { value: 0.13 },
    'burden.labels': {},
    'notice.disclaimer': { text: '고지' },
    'notice.multipleTargets': { text: '2인 이상' },
    'undecidable.noticeText': { text: '판정 불가' },
    'notice.inferenceUnavailable': { text: '지금은 진단 결과를 드릴 수 없습니다.' },
  } as any)[k],
}));
vi.mock('../../src/repositories/pool.js', () => ({ query: async () => [] }));
vi.mock('../../src/services/referralService.js', () => ({
  buildReferral: async () => ({ facilities: [{ name: '가까운 센터' }] }),
}));

const { diagnose } = await import('../../src/services/diagnosisService.js');

const PARAMS = {
  answers: [{ questionNo: 1, value: 4 }], careTargetAge: 20,
  multipleCareTargets: false, lat: null, lng: null, regionCode: null,
};

describe('추론 서비스 장애', () => {
  it('판정을 내지 않는다', async () => {
    const out = await diagnose(PARAMS);
    expect(out.decided).toBe(false);
    expect(out.unavailable).toBe(true);
    expect(out.burdenLabel).toBeNull();
    expect(out.internalLabel).toBeNull();
    expect(out.contributions).toBeNull();
    expect(out.comparison).toBeNull();
  });

  it('장애 안내를 낸다 — 판정 불가 문구와 다르다', async () => {
    const out = await diagnose(PARAMS);
    expect(out.unavailableNotice).toContain('진단 결과를 드릴 수 없습니다');
    expect(out.undecidableNotice).toBeNull();
  });

  it('기관 안내는 그대로 제공한다', async () => {
    const out = await diagnose(PARAMS);
    expect(out.immediateReferral).not.toBeNull();
  });
});
