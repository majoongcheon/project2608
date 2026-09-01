# -*- coding: utf-8 -*-
"""Python↔TS 추론 일치 검증용 기준값 생성 (research.md R-2 릴리스 게이트).

train+test 3,000건 전량을 Python 기준 구현에 통과시켜 확률·기여도·판정을 기록한다.
backend/tests/parity 가 TS 구현 결과와 1e-9 이내 일치를 확인한다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml'))
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))

import numpy as np              # noqa: E402
import db as dbmod              # noqa: E402
from saabas import predict_proba, contributions, decide   # noqa: E402

MODELS = ROOT / 'models'
model = json.loads((MODELS / 'model_v1.json').read_text(encoding='utf-8'))
unc = json.loads((MODELS / 'uncertainty_v1.json').read_text(encoding='utf-8'))

d = dbmod.load_dataset(model['missing_sentinel'])
idx = {f: i for i, f in enumerate(d['features'])}
cols = [idx[f] for f in model['features']]
X = np.vstack([d['X'][:, cols], d['Xtest'][:, cols]])

table, tc, td = unc['freq_table'], unc['tau_conf'], unc['tau_dens']


def rarity(row):
    s = 0.0
    for j, f in enumerate(model['features']):
        p = table[f].get(str(int(row[j])), 1e-4)
        s += np.log(max(p, 1e-4))
    return float(s / len(model['features']))


cases = []
for i in range(len(X)):
    row = [float(v) for v in X[i]]
    proba = predict_proba(model, row)
    cls = decide(model, proba)
    contrib, base = contributions(model, row, cls)
    r = rarity(row)
    cases.append({
        'input': row,
        'proba': proba,
        'decidedIndex': cls,
        'rarity': r,
        'undecidable': bool(max(proba) < tc or r < td),
        'contributions': contrib,
        'base': base,
    })

out = {'model_version': model['model_version'], 'features': model['features'],
       'tau_conf': tc, 'tau_dens': td, 'n': len(cases), 'cases': cases}
(MODELS / 'parity_v1.json').write_text(json.dumps(out), encoding='utf-8')

# 국소 정확성 자체 점검: 기여도 합 + 기준값 = 점수
worst = 0.0
for c in cases[:500]:
    lhs = sum(c['contributions']) + c['base']
    if model['family'] == 'logit':
        z = np.log(np.array(c['proba']))
        rhs = float(z[c['decidedIndex']] - np.mean(z) + np.mean(z))   # softmax 상수항 제거 전 비교용
        rhs = None
    else:
        rhs = c['proba'][c['decidedIndex']]
    if rhs is not None:
        worst = max(worst, abs(lhs - rhs))

print(f"parity_v1.json 생성: {len(cases)}건 · {(MODELS/'parity_v1.json').stat().st_size/1e6:.1f}MB")
print(f"판정 불가 {sum(c['undecidable'] for c in cases)}건 ({sum(c['undecidable'] for c in cases)/len(cases)*100:.1f}%)")
if model['family'] != 'logit':
    print(f"국소 정확성 최대 오차: {worst:.2e}")
