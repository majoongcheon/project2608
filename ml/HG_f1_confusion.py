"""읽기 전용 — train OOF 혼동행렬. test 602건은 건드리지 않는다."""
import sys, json, numpy as np
sys.path.insert(0, 'ml/.pylibs'); sys.path.insert(0, 'ml')
from cb_burden.data import snapshot
from cb_burden.stages import _core
from sklearn.metrics import confusion_matrix

snap = snapshot.read('data/snapshots/cb_dataset_2026-09-01.csv.gz')
dep = json.load(open('models/v1.0.0/model_v1.json'))
feats7, w = dep['features'], dep['decision_weights']
X, y, folds = _core.train_view(snap)
X7 = X[:, [snap['features'].index(f) for f in feats7]]
r = _core.cv_scores(X7, y, folds, feats7, family='logit', weights=w)
pred = _core.decide(r['oof_proba'], w)

C = [1,2,3,4,5]
cm = confusion_matrix(y, pred, labels=C)
NAMES = {1:'최고부담',2:'고부담',3:'중간',4:'저부담',5:'없음'}

print("행=실제 · 열=예측 (train 2,398건 OOF)\n")
print("실제\\예측      1최고   2고    3중간  4저    5없음  |  합계   정답률")
for i,c in enumerate(C):
    row=cm[i]; tot=row.sum()
    cells=" ".join(f"{v:6d}" for v in row)
    print(f"  {c} {NAMES[c]:4s}  {cells}  | {tot:5d}   {row[i]/tot:5.1%}")
print(f"  합계       " + " ".join(f"{v:6d}" for v in cm.sum(axis=0)) + f"  | {cm.sum():5d}")

print("\n--- 오류의 거리 ---")
d = np.abs(np.asarray(y) - np.asarray(pred))
for k in range(5):
    n=int((d==k).sum())
    print(f"  {k}칸 차이 {n:5d}  {n/len(y):6.1%}" + ("   ← 정답" if k==0 else ""))
print(f"  1칸 이내 누적 {int((d<=1).sum())/len(y):.1%}")

print("\n--- 서비스 관점: 고부담(1~2) vs 그 외 2분류 ---")
ah = np.asarray(y)<=2; ph = np.asarray(pred)<=2
tp=int((ah&ph).sum()); fn=int((ah&~ph).sum()); fp=int((~ah&ph).sum()); tn=int((~ah&~ph).sum())
print(f"  실제 고부담 {ah.sum():4d} → 고부담 판정 {tp:4d} · 놓침 {fn:4d}   재현율 {tp/ah.sum():.1%}")
print(f"  실제 그 외 {(~ah).sum():4d} → 고부담 오판 {fp:4d} · 정상 {tn:4d}   정밀도 {tp/(tp+fp):.1%}")
print(f"  2분류 정확도 {(tp+tn)/len(y):.1%}")

print("\n--- 1등급을 어디로 보내나 ---")
row1=cm[0]
for j,c in enumerate(C):
    print(f"  1등급 → {c}({NAMES[c]}) {row1[j]:4d}  {row1[j]/row1.sum():5.1%}"
          + ("   경고·즉시안내 동일" if c<=2 else ""))
