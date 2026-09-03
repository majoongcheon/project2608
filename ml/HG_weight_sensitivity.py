"""가중치 1.1 → 1.0 영향 측정 (읽기 전용, train OOF, test 미사용)."""
import sys, json
sys.path.insert(0,'ml/.pylibs'); sys.path.insert(0,'ml')
import numpy as np
from cb_burden.data import snapshot
from cb_burden.stages import _core

snap = snapshot.read('data/snapshots/cb_dataset_2026-09-01.csv.gz')
dep = json.load(open('models/model_v1.json'))
f7 = dep['features']
m = snap['split'] == 'train'
X, y, folds = snap['X'][m], snap['y'][m], snap['cv_fold'][m]
X7 = X[:, [snap['features'].index(f) for f in f7]]

r = _core.cv_scores(X7, y, folds, f7, family='logit')   # 확률은 가중치와 무관
proba = r['oof_proba']

def report(w, name):
    pred = _core.decide(proba, w)
    return {
        'name': name, 'pred': pred,
        'macro_f1': _core.macro_f1(y, pred),
        'rec': _core.high_burden_recall(y, pred),
        'acc': float((pred == y).mean()),
        'hb_pred': int((pred <= 2).sum()),
        'hb_acc': float(((pred <= 2) == (y <= 2)).mean()),
        'hb_prec': float(((pred <= 2) & (y <= 2)).sum() / max((pred <= 2).sum(), 1)),
    }

a = report([1.1,1.1,1,1,1], '현재 1.1')
b = report([1.0,1.0,1,1,1], '변경 1.0')
print(f"{'':10s} {'macroF1':>8s} {'고부담재현율':>10s} {'정확도':>7s} {'고부담판정수':>10s} {'고부담정밀도':>10s} {'2분류정확도':>10s}")
for x in (a, b):
    print(f"{x['name']:10s} {x['macro_f1']:8.4f} {x['rec']:10.4f} {x['acc']:7.4f} "
          f"{x['hb_pred']:10d} {x['hb_prec']:10.4f} {x['hb_acc']:10.4f}")
print(f"{'차이':10s} {b['macro_f1']-a['macro_f1']:+8.4f} {b['rec']-a['rec']:+10.4f} "
      f"{b['acc']-a['acc']:+7.4f} {b['hb_pred']-a['hb_pred']:+10d} "
      f"{b['hb_prec']-a['hb_prec']:+10.4f} {b['hb_acc']-a['hb_acc']:+10.4f}")

ch = a['pred'] != b['pred']
print(f"\n등급이 바뀌는 사람  {int(ch.sum())}명 / {len(y)}  ({ch.mean()*100:.2f}%)")
if ch.sum():
    from collections import Counter
    c = Counter(zip(a['pred'][ch].tolist(), b['pred'][ch].tolist()))
    print('   변화 내역 (현재 → 변경):')
    for (p1,p2), n in sorted(c.items(), key=lambda x:-x[1]):
        print(f'     {p1}등급 → {p2}등급   {n}명')

lost = (a['pred'] <= 2) & (b['pred'] > 2)
print(f"\n고부담 판정을 잃는 사람  {int(lost.sum())}명")
print(f"   그 중 실제 고부담      {int((lost & (y <= 2)).sum())}명   ← 놓치게 되는 사람")
print(f"   그 중 실제 비고부담    {int((lost & (y > 2)).sum())}명   ← 오판이 줄어드는 것")

# ── 가중치를 훑어본다 — 왜 1.1 인가
print('\n가중치 훑기 (train OOF · 학습이 요구하는 하한 0.73)')
print(f"{'가중치':>6s} {'macroF1':>8s} {'고부담재현율':>10s} {'고부담판정수':>10s} {'하한충족':>8s}")
best = (None, -1.0)
for w in np.arange(1.00, 1.61, 0.05):
    pred = _core.decide(proba, [w, w, 1, 1, 1])
    f1 = _core.macro_f1(y, pred); rec = _core.high_burden_recall(y, pred)
    ok = rec >= 0.73
    if ok and f1 > best[1]:
        best = (round(float(w), 2), f1)
    mark = '  O' if ok else '  X'
    star = '  ★배포값' if abs(w - 1.1) < 1e-9 else ''
    print(f"{w:6.2f} {f1:8.4f} {rec:10.4f} {int((pred<=2).sum()):10d} {mark}{star}")
print(f"\n하한을 지키면서 macro F1 이 가장 높은 가중치 = {best[0]}  (F1 {best[1]:.4f})")
