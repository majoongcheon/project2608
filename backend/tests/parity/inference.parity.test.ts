// 릴리스 게이트 (research.md R-2)
//   Python 학습기(ml/saabas.py)와 TS 추론기가 같은 답을 내는지 3,000건 전량으로 확인한다.
//   실패하면 배포하지 않는다 — 두 구현이 갈라진 상태에서는 원칙 IV(재현성)가 성립하지 않는다.
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { predictProba, decide, contributions } from '../../src/inference/predictor.js';
import { rarity, isUndecidable } from '../../src/inference/undecidable.js';
import type { ModelPayload, Uncertainty } from '../../src/inference/types.js';

const ROOT = path.resolve(__dirname, '..', '..', '..');
const model: ModelPayload = JSON.parse(fs.readFileSync(path.join(ROOT, 'models/model_v1.json'), 'utf8'));
const unc: Uncertainty = JSON.parse(fs.readFileSync(path.join(ROOT, 'models/uncertainty_v1.json'), 'utf8'));
const fixture = JSON.parse(fs.readFileSync(path.join(ROOT, 'models/parity_v1.json'), 'utf8'));

const TOL = 1e-9;

describe('Python ↔ TS 추론 패리티', () => {
  it('아티팩트와 기준값의 모델 버전이 같다', () => {
    expect(fixture.model_version).toBe(model.model_version);
    expect(fixture.features.join(',')).toBe(model.features.join(','));
  });

  it(`클래스 확률이 ${TOL} 이내로 일치한다 (${fixture.n}건)`, () => {
    let worst = 0;
    for (const c of fixture.cases) {
      const p = predictProba(model, c.input);
      for (let i = 0; i < p.length; i++) worst = Math.max(worst, Math.abs(p[i] - c.proba[i]));
    }
    expect(worst).toBeLessThan(TOL);
  });

  it('판정 구간이 100% 일치한다', () => {
    let mismatch = 0;
    for (const c of fixture.cases) {
      if (decide(model, predictProba(model, c.input)) !== c.decidedIndex) mismatch++;
    }
    expect(mismatch).toBe(0);
  });

  it('희소성과 판정 불가 판단이 일치한다', () => {
    let worst = 0, mismatch = 0;
    for (const c of fixture.cases) {
      const r = rarity(model, unc, c.input);
      worst = Math.max(worst, Math.abs(r - c.rarity));
      const p = predictProba(model, c.input);
      if (isUndecidable(p, r, fixture.tau_conf, fixture.tau_dens) !== c.undecidable) mismatch++;
    }
    expect(worst).toBeLessThan(TOL);
    expect(mismatch).toBe(0);
  });

  it('기여도와 기준값이 일치한다', () => {
    let worst = 0;
    for (const c of fixture.cases) {
      const { contrib, base } = contributions(model, c.input, c.decidedIndex);
      worst = Math.max(worst, Math.abs(base - c.base));
      for (let i = 0; i < contrib.length; i++) {
        worst = Math.max(worst, Math.abs(contrib[i] - c.contributions[i]));
      }
    }
    expect(worst).toBeLessThan(TOL);
  });
});
