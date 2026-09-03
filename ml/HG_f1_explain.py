"""읽기 전용 — 배포본과 같은 설정으로 train OOF 예측을 만들어 등급별 F1 을 본다.
test 602건은 건드리지 않는다."""
import sys, json, numpy as np
sys.path.insert(0, 'ml/.pylibs'); sys.path.insert(0, 'ml')
from cb_burden.data import snapshot
from cb_burden.stages import _core
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix

snap = snapshot.read('data/snapshots/cb_dataset_2026-09-01.csv.gz')
dep = json.load(open('models/v1.0.0/model_v1.json'))
feats7, w = dep['features'], dep['decision_weights']

X, y, folds = _core.train_view(snap)
idx = [snap['features'].index(f) for f in feats7]
X7 = X[:, idx]

r = _core.cv_scores(X7, y, folds, feats7, family='logit', weights=w)
pred = _core.decide(r['oof_proba'], w)

C = [1,2,3,4,5]
p = precision_score(y, pred, labels=C, average=None, zero_division=0)
rc = recall_score(y, pred, labels=C, average=None, zero_division=0)
f1 = f1_score(y, pred, labels=C, average=None, zero_division=0)

print("등급  실제인원  예측인원   정밀도   재현율     F1")
for i, c in enumerate(C):
    print(f"  {c}   {int((y==c).sum()):6d}  {int((pred==c).sum()):7d}   "
          f"{p[i]:6.3f}   {rc[i]:6.3f}  {f1[i]:6.3f}")
print()
print(f"macro F1     {f1.mean():.4f}   ← 5개를 단순 평균")
print(f"weighted F1  {f1_score(y,pred,labels=C,average='weighted',zero_division=0):.4f}   ← 인원수 가중")
print(f"micro F1     {f1_score(y,pred,labels=C,average='micro',zero_division=0):.4f}   ← 사실상 정확도")
print(f"고부담(1~2) 재현율 {_core.high_burden_recall(y,pred):.4f}")
print()
print("5등급 F1 을 0.05 흔들면 macro 는", f"{(f1.sum()+0.05)/5 - f1.mean():+.4f} 움직인다")
