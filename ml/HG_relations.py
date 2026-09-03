"""관계 기술·인과 한계 측정 (읽기 전용).

train 2,398건만 읽는다. test 602건·DB·배포본은 건드리지 않는다.
  ① 38변수 각각과 care_burden 의 순위상관 (스피어만)
  ② 배포 7문항 응답 조합별 라벨 일관성 — "같은 답인데 라벨이 갈리는가"
  ③ 조합 기준 상한(천장) — 조합마다 최빈 라벨을 찍었을 때의 정확도
"""
import sys, json
from collections import defaultdict
sys.path.insert(0, 'ml/.pylibs'); sys.path.insert(0, 'ml')
import numpy as np
from cb_burden.data import snapshot

snap = snapshot.read('data/snapshots/cb_dataset_2026-09-01.csv.gz')
m = snap['split'] == 'train'
X, y = snap['X'][m], snap['y'][m]
feats = snap['features']
dep = json.load(open('models/model_v1.json'))['features']


def rankdata(a):
    """평균 순위 (동점 처리)."""
    a = np.asarray(a, dtype=float)
    order = a.argsort(kind='mergesort')
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1)
    # 동점 평균
    vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(vals))
    np.add.at(sums, inv, ranks)
    return (sums / cnt)[inv]


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ra, rb = ra - ra.mean(), rb - rb.mean()
    d = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / d) if d else 0.0


print('① 순위상관 — care_burden(1=최고부담) 과의 스피어만')
print('   양수 = 값이 클수록 부담이 작다 / 음수 = 값이 클수록 부담이 크다\n')
rows = []
for j, f in enumerate(feats):
    col = X[:, j]
    ok = col != -1                      # 결측(-1)은 제외하고 잰다
    if ok.sum() < 30:
        continue
    rows.append((abs(spearman(col[ok], y[ok])), spearman(col[ok], y[ok]), f, int(ok.sum())))
rows.sort(reverse=True)
print('   상위 12개')
for a, r, f, n in rows[:12]:
    mark = ' ★배포문항' if f in dep else ''
    print(f'   {r:+.3f}  {f:34s} n={n:4d}{mark}')
print('\n   배포 7문항')
for a, r, f, n in sorted([x for x in rows if x[2] in dep], reverse=True):
    print(f'   {r:+.3f}  {f:34s} n={n:4d}')

# ─────────────────────────────────────────────────────────
idx = [feats.index(f) for f in dep]
X7 = X[:, idx]
combo = defaultdict(list)
for i in range(len(X7)):
    combo[tuple(X7[i])].append(int(y[i]))

multi = {k: v for k, v in combo.items() if len(v) >= 2}
split_lab = sum(1 for v in multi.values() if len(set(v)) > 1)
split_hb = sum(1 for v in multi.values() if len(set(l <= 2 for l in v)) > 1)
n_multi_people = sum(len(v) for v in multi.values())

print(f'\n② 응답 조합별 라벨 일관성 — 배포 7문항')
print(f'   서로 다른 조합        {len(combo):5d}개')
print(f'     1명짜리            {len(combo) - len(multi):5d}개  ({(len(combo)-len(multi))/len(combo)*100:.1f}%)')
print(f'     2명 이상           {len(multi):5d}개  (해당 인원 {n_multi_people}명)')
print(f'   2명 이상 조합 중')
print(f'     라벨이 갈림        {split_lab:5d}개  {split_lab/len(multi)*100:.1f}%')
print(f'     고부담 여부가 갈림  {split_hb:5d}개  {split_hb/len(multi)*100:.1f}%')

# ③ 천장
hit_all = sum(max(set(v), key=v.count) == l for v in combo.values() for l in v)
hit_multi = sum(max(set(v), key=v.count) == l for v in multi.values() for l in v)
hb_multi = sum((max(set([x <= 2 for x in v]), key=[x <= 2 for x in v].count)) == (l <= 2)
               for v in multi.values() for l in v)
print(f'\n③ 조합 기준 상한 — 조합마다 최빈 라벨을 찍는다면')
print(f'   전체 2,398건 기준        {hit_all/len(y)*100:.1f}%   ← 1명짜리가 자동 정답이라 부풀려진 값')
print(f'   2명 이상 조합만 ({n_multi_people}명)  {hit_multi/n_multi_people*100:.1f}%   ← 정직한 상한')
print(f'   같은 기준 고부담 2분류    {hb_multi/n_multi_people*100:.1f}%')

# ─────────────────────────────────────────────────────────
# ④ 공정한 비교 — 상한과 같은 집단(2명 이상 조합 1,568명)에서 모델 성적을 잰다
from cb_burden.stages import _core
w = json.load(open('models/model_v1.json'))['decision_weights']
r = _core.cv_scores(X7, y, snap['cv_fold'][m], dep, family='logit', weights=w)
pred = _core.decide(r['oof_proba'], w)

multi_mask = np.array([len(combo[tuple(row)]) >= 2 for row in X7])
acc_all = float((pred == y).mean())
acc_multi = float((pred[multi_mask] == y[multi_mask]).mean())
hb_acc_multi = float(((pred[multi_mask] <= 2) == (y[multi_mask] <= 2)).mean())

print(f'\n④ 상한과 같은 집단에서의 모델 성적 (2명 이상 조합 {int(multi_mask.sum())}명)')
print(f'   5등급 정확도   모델 {acc_multi*100:.1f}%  vs  상한 {hit_multi/n_multi_people*100:.1f}%'
      f'   → 남은 여지 {hit_multi/n_multi_people*100 - acc_multi*100:.1f}%p')
print(f'   고부담 2분류   모델 {hb_acc_multi*100:.1f}%  vs  상한 {hb_multi/n_multi_people*100:.1f}%'
      f'   → 남은 여지 {hb_multi/n_multi_people*100 - hb_acc_multi*100:.1f}%p')
print(f'   (참고) 전체 2,398건 5등급 정확도 {acc_all*100:.1f}%')
