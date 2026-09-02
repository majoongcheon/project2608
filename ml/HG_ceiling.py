"""이 7문항으로 도달 가능한 최대 정확도 (읽기 전용).

같은 답을 한 사람들끼리 실제 부담이 갈리면 **어떤 모델도 그건 못 맞힌다.**
그 한계를 재는 스크립트다. "모델을 바꾸면 나아질까"에 답한다.

    PYTHONPATH=ml/.pylibs:ml python3 ml/HG_ceiling.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'ml'))

from cb_burden.data import snapshot                                   # noqa: E402

m = json.loads((ROOT / 'models' / 'model_v1.json').read_text(encoding='utf-8'))
snap = snapshot.read(ROOT / 'data' / 'snapshots' / 'cb_dataset_2026-09-01.csv.gz')
idx = {f: i for i, f in enumerate(snap['features'])}
cols = [idx[f] for f in m['features']]
X, y = snap['X'][:, cols], snap['y']

groups = defaultdict(list)
for i in range(len(y)):
    groups[tuple(X[i])].append(int(y[i]))

n = len(y)
dup = {k: v for k, v in groups.items() if len(v) > 1}
conflict = {k: v for k, v in dup.items() if len(set(v)) > 1}

print(f'전체 {n}명 · 서로 다른 답변 조합 {len(groups)}가지')
print(f'2명 이상이 똑같이 답한 조합 {len(dup)}가지 ({sum(len(v) for v in dup.values())}명)')
print(f'  그중 부담 수준이 갈리는 조합 {len(conflict)}가지 ({len(conflict)/len(dup)*100:.1f}%)')

best5 = sum(Counter(v).most_common(1)[0][1] for v in groups.values())
best2 = sum(max(sum(1 for x in v if x <= 2), sum(1 for x in v if x > 2))
            for v in groups.values())
print(f'\n도달 가능한 최대 정확도')
print(f'  5구간      {best5}/{n} = {best5/n*100:.1f}%')
print(f'  고부담 여부 {best2}/{n} = {best2/n*100:.1f}%')
print(f'\n갈리는 사례 (같은 답인데 실제 부담이 다름)')
for k, v in list(conflict.items())[:3]:
    print(f'  {[int(x) for x in k]} → {sorted(v)}')
