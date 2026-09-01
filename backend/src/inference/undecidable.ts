// 판정 불가 판단 (FR-009a·FR-009b)
//   두 신호를 OR 로 묶는다.
//     확신도 : 최대 클래스 확률이 낮다 — 어느 구간도 자신 있게 고르지 못함
//     희소성 : 학습 분포에서 드문 응답 조합 — 데이터가 뒷받침하지 못함
//   임계값은 학습으로 보정된 값이며 설정에서 읽는다 (FR-009c).
import type { ModelPayload, Uncertainty } from './types.js';

const EPS = 1e-4;

export function rarity(model: ModelPayload, unc: Uncertainty, row: number[]): number {
  let s = 0;
  for (let j = 0; j < model.features.length; j++) {
    const table = unc.freq_table[model.features[j]] ?? {};
    const p = table[String(Math.trunc(row[j]))] ?? EPS;
    s += Math.log(Math.max(p, EPS));
  }
  return s / model.features.length;
}

export function isUndecidable(
  proba: number[], rar: number, tauConf: number, tauDens: number
): boolean {
  return Math.max(...proba) < tauConf || rar < tauDens;
}
