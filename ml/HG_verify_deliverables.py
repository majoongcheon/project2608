"""제출물 검증 — deliverables/predict.py 가 운영 판정과 같은 답을 내는가.

같은 계산이 두 벌(ml/cb_burden/serve/engine.py 와 deliverables/predict.py)이 되었으므로
갈라지면 조용히 다른 판정이 나간다. models/parity_v1.json 3,000건으로 대조한다.
읽기 전용 — 아무 파일도 쓰지 않는다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'deliverables'))

import numpy as np
import predict as P

fx = json.loads((ROOT / 'models' / 'parity_v1.json').read_text(encoding='utf-8'))
cases = fx['cases']
P._load()
qs = P._schema['questions']
sentinel = P._policy['missing_sentinel']
w = P._policy['decision_weights']

worst_proba = worst_rar = worst_contrib = worst_base = 0.0
bad_label = bad_und = 0

for c in cases:
    row = c['input']
    # 학습 데이터를 그대로 재현한다 — 결측은 null 이 아니라 센티널(-1) 로 넣는다.
    # 화면에 '해당 없음' 선택지가 없는 문항에도 학습 데이터에는 결측이 있기 때문이다.
    payload = {'answers': [
        {'questionNo': q['questionNo'], 'value': int(row[j])}
        for j, q in enumerate(qs)]}
    got = P.predict(payload)

    worst_proba = max(worst_proba, float(np.abs(
        np.array(got['proba']) - np.array(c['proba'])).max()))
    worst_rar = max(worst_rar, abs(got['rarity'] - c['rarity']))

    if got['decided'] == c['undecidable']:
        bad_und += 1                       # decided 와 undecidable 은 서로 반대여야 한다
    if not c['undecidable']:
        idx = max(range(len(c['proba'])), key=lambda i: c['proba'][i] * w[i])
        if got['internalLabel'] != P._policy['classes'][idx] or idx != c['decidedIndex']:
            bad_label += 1
        contrib, base = P.contributions_all(row, idx)
        worst_contrib = max(worst_contrib, float(np.abs(
            np.array(contrib) - np.array(c['contributions'])).max()))
        worst_base = max(worst_base, abs(base - c['base']))

n_und = sum(1 for c in cases if c['undecidable'])
print(f'대조 {len(cases):,}건 (판정 성립 {len(cases)-n_und:,} · 판정 불가 {n_und})')
print(f'   확률      최대 오차 {worst_proba:.3e}')
print(f'   희소성    최대 오차 {worst_rar:.3e}')
print(f'   기여도    최대 오차 {worst_contrib:.3e}')
print(f'   기준값    최대 오차 {worst_base:.3e}')
print(f'   판정 불가 불일치 {bad_und}건')
print(f'   등급      불일치 {bad_label}건')

TOL = 1e-9
ok = (worst_proba < TOL and worst_rar < TOL and worst_contrib < TOL
      and worst_base < TOL and bad_und == 0 and bad_label == 0)
print('\n' + ('통과 — 제출물과 운영 판정이 같다' if ok else '★실패 — 두 구현이 갈렸다'))
sys.exit(0 if ok else 1)
