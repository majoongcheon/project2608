// 추론과 기여도 — ml/saabas.py 의 TS 이식본.
// 두 구현이 같은 결과를 내는지는 tests/parity 가 3,000건으로 보증한다 (research.md R-2).
import type { ModelPayload } from './types.js';

function softmax(z: number[]): number[] {
  const m = Math.max(...z);
  const e = z.map((v) => Math.exp(v - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / s);
}

function catIndex(model: ModelPayload, j: number, value: number): number {
  const cats = model.categories![j];
  for (let i = 0; i < cats.length; i++) if (cats[i] === value) return i;
  return -1;                                   // 미지의 값 → 원-핫 전부 0
}

function logitScores(model: ModelPayload, row: number[]): number[] {
  const z = [...model.intercept!];
  for (let j = 0; j < model.features.length; j++) {
    const idx = catIndex(model, j, row[j]);
    if (idx < 0) continue;
    const col = model.spans![j][0] + idx;
    for (let c = 0; c < z.length; c++) z[c] += model.coef![c][col];
  }
  return z;
}

function treeProba(model: ModelPayload, row: number[]): number[] {
  const trees = model.trees!;
  const nc = model.classes.length;
  const acc = new Array(nc).fill(0);
  for (const t of trees) {
    let node = 0;
    while (t.left[node] !== -1) {
      const f = t.feature[node];
      node = row[f] <= t.threshold[node] ? t.left[node] : t.right[node];
    }
    for (let c = 0; c < nc; c++) acc[c] += t.value[node][c];
  }
  return acc.map((a) => a / trees.length);
}

export function predictProba(model: ModelPayload, row: number[]): number[] {
  return model.family === 'logit' ? softmax(logitScores(model, row)) : treeProba(model, row);
}

/** 결정 가중치를 적용해 최종 구간 인덱스를 고른다 (SC-005 — 고부담을 놓치지 않는 쪽으로). */
export function decide(model: ModelPayload, proba: number[]): number {
  const w = model.decision_weights ?? proba.map(() => 1);
  let best = 0;
  for (let i = 1; i < proba.length; i++) if (proba[i] * w[i] > proba[best] * w[best]) best = i;
  return best;
}

/** 변수별 기여도와 기준값. sum(contrib) + base = 점수 가 정확히 성립한다. */
export function contributions(
  model: ModelPayload, row: number[], cls: number
): { contrib: number[]; base: number } {
  if (model.family === 'logit') {
    const contrib = model.features.map((_, j) => {
      const idx = catIndex(model, j, row[j]);
      const actual = idx < 0 ? 0 : model.coef![cls][model.spans![j][0] + idx];
      return actual - model.expected_contrib![j][cls];
    });
    const base = model.intercept![cls] +
      model.expected_contrib!.reduce((s, e) => s + e[cls], 0);
    return { contrib, base };
  }

  const trees = model.trees!;
  const contrib = new Array(model.features.length).fill(0);
  let base = 0;
  for (const t of trees) {
    let node = 0;
    base += t.value[0][cls];
    while (t.left[node] !== -1) {
      const f = t.feature[node];
      const next = row[f] <= t.threshold[node] ? t.left[node] : t.right[node];
      contrib[f] += t.value[next][cls] - t.value[node][cls];
      node = next;
    }
  }
  return { contrib: contrib.map((c) => c / trees.length), base: base / trees.length };
}
