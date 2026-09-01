# -*- coding: utf-8 -*-
"""발표 차트용 수치 계산. 혼동행렬은 반드시 **교차검증(train 2,398건)** 기준으로만 낸다.
test 602건은 '단 한 번만 사용' 규칙이 걸려 있어 k 별로 여러 번 열면 SC 판정 근거가 무효가 된다."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs')); sys.path.insert(0, str(ROOT / 'ml'))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import confusion_matrix
import db as dbmod
from train import decide, tune_decision_weights, macro_f1, high_burden_recall, CLASSES, SEED, MISSING

d = dbmod.load_dataset(MISSING)
X, y, folds, feats = d['X'], d['y'], d['folds'], d['features']
sel = json.loads((ROOT / 'models/selection_v1.json').read_text(encoding='utf-8'))
idx = {f: i for i, f in enumerate(feats)}
dropped = sel['dropped_order']

FSETS = {
    38: list(feats),
    7:  list(sel['selected']),
    6:  [f for f in feats if f not in set(dropped[:32])],
}
out = {'k_sets': {str(k): v for k, v in FSETS.items()}}
print('문항 집합:', {k: len(v) for k, v in FSETS.items()})

def oof(cols):
    proba = np.zeros((len(y), len(CLASSES)))
    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        m = LogisticRegression(max_iter=2000, random_state=SEED)
        m.fit(enc.fit_transform(X[tr][:, cols]), y[tr])
        proba[va] = m.predict_proba(enc.transform(X[va][:, cols]))
    return proba

# ── B. k별 혼동행렬 (CV) ───────────────────────────────────────────
out['confusion'] = {}
for k, fs in FSETS.items():
    cols = [idx[f] for f in fs]
    p = oof(cols)
    w, tuned = tune_decision_weights(p, y)
    pred = decide(p, w)
    cm5 = confusion_matrix(y, pred, labels=CLASSES)
    hb_true, hb_pred = (y <= 2), (pred <= 2)
    cm2 = np.array([[int((hb_true & hb_pred).sum()),  int((hb_true & ~hb_pred).sum())],
                    [int((~hb_true & hb_pred).sum()), int((~hb_true & ~hb_pred).sum())]])
    rec = cm2[0, 0] / cm2[0].sum()
    out['confusion'][str(k)] = {
        'cm5': cm5.tolist(), 'cm2': cm2.tolist(),
        'macro_f1': tuned['macro_f1'], 'recall': float(rec),
        'accuracy': float((pred == y).mean()),
    }
    print('  k=%2d  F1 %.4f · 고부담재현율 %.4f · 정확도 %.4f' % (k, tuned['macro_f1'], rec, (pred == y).mean()))

# ── C. 문항 수별 성능 곡선 ─────────────────────────────────────────
out['curve'] = [{'k': h['k'], 'f1': h['macro_f1'], 'recall': h['high_burden_recall'],
                 'passes': h['passes']} for h in sel['history']]

# ── D. MI 설명력 (잔존 38 + 배제 6) ────────────────────────────────
def mi_over_h(x, yy, bins=None):
    xs = x.copy().astype(float)
    if bins:
        q = np.quantile(xs[~np.isnan(xs)], np.linspace(0, 1, bins + 1)[1:-1])
        xs = np.digitize(xs, q).astype(float)
    vals = np.unique(xs); ys = np.unique(yy); n = len(yy)
    mi = 0.0
    for v in vals:
        px = (xs == v).mean()
        for c in ys:
            pxy = ((xs == v) & (yy == c)).mean()
            if pxy > 0:
                mi += pxy * np.log(pxy / (px * (yy == c).mean()))
    hy = -sum((yy == c).mean() * np.log((yy == c).mean()) for c in ys)
    return mi / hy * 100

CONT = {'caregiver_age', 'age_disability_suspected', 'household_size', 'past_job_count'}
mi = []
for f in feats:
    mi.append({'feature': f, 'mi': mi_over_h(X[:, idx[f]], y, bins=10 if f in CONT else None),
               'excluded': False})
EXCL = [('caregiver_life_satisfaction', 19.06), ('care_difficulty_top1', 6.88),
        ('needed_care_service_type', 4.98), ('work_care_gap_hours', 1.08),
        ('work_care_gap_exp', 0.62), ('integrated_care_awareness', 0.36)]
for f, v in EXCL:
    mi.append({'feature': f, 'mi': v, 'excluded': True})
out['mi'] = sorted(mi, key=lambda r: -r['mi'])
out['selected7'] = FSETS[7]
print('  MI 계산 완료 — 잔존 38 + 배제 6')

# ── E. PCA 산점도 ──────────────────────────────────────────────────
# notebooks/HG-실험-군집화.ipynb 와 **동일한 전처리**를 쓴다 —
#   원-핫(38변수 → 326열) 후 표준화 없이 PCA. 표준화를 넣으면 PC1 이 4.6% 로 희석되어
#   팀 문서에 기록된 12.9% 와 어긋난다.
enc_p = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
Xo = enc_p.fit_transform(X)
Z = PCA(n_components=2, random_state=SEED).fit(Xo)
P = Z.transform(Xo)
out['pca'] = {'x': P[:, 0].tolist(), 'y': P[:, 1].tolist(), 'label': y.tolist(),
              'evr': [float(v) for v in Z.explained_variance_ratio_]}
print('  PCA 설명력: PC1 %.1f%% · PC2 %.1f%%' % (Z.explained_variance_ratio_[0]*100, Z.explained_variance_ratio_[1]*100))

# 군집화 지표 — HG-실험-군집화.ipynb 의 실측 출력값
out['cluster'] = {
    'k': list(range(2, 11)),
    'silhouette': [0.1233, 0.1153, 0.1075, 0.1090, 0.1034, 0.1000, 0.1064, 0.0999, 0.0944],
    'ari':        [0.0308, 0.0206, 0.0306, 0.0269, 0.0195, 0.0214, 0.0215, 0.0126, 0.0157],
}

(ROOT / 'docs/assets').mkdir(parents=True, exist_ok=True)
(ROOT / 'docs/assets/chart_data.json').write_text(json.dumps(out), encoding='utf-8')
print('저장: docs/assets/chart_data.json')
