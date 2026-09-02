# -*- coding: utf-8 -*-
"""SJH-01 · 모델 계열 비교와 앙상블 실험 (신지현).

배포 파이프라인(ml/train.py)을 건드리지 않는 읽기 전용 실험이다.
models/ 에 아무것도 쓰지 않고, 결과는 docs/SJH-모델비교-결과.json 으로만 남긴다.

★ test 602건은 절대 사용하지 않는다. train 2,398건의 DB 고정 cv_fold 5-fold 만 쓴다.
  (ml/README.md "지켜야 할 것" — test 를 실험에 쓰면 최종 근거로 못 쓴다)

  python3 ml/SJH-model-benchmark.py
"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs-sjh'))
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'ml'))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (RandomForestClassifier, ExtraTreesClassifier,
                              HistGradientBoostingClassifier)
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import f1_score, accuracy_score
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

import db as dbmod

SEED = 20260901
CLASSES = [1, 2, 3, 4, 5]
MISSING = -1
MIN_REC_ABS, REC_MARGIN = 0.70, 0.03


def macro_f1(y, p):
    return float(f1_score(y, p, average='macro', labels=CLASSES, zero_division=0))


def hb_recall(y, p):
    y, p = np.asarray(y), np.asarray(p)
    a = (y <= 2)
    return float(((p <= 2) & a).sum() / a.sum()) if a.sum() else 0.0


def decide(proba, w=None):
    p = np.asarray(proba, float)
    if w is not None:
        p = p * np.asarray(w, float)
    return np.asarray(CLASSES)[p.argmax(axis=1)]


def tune_weights(proba, y):
    """train.py 와 같은 규칙. OOF 확률에서만 고른다(test 미사용)."""
    best = (None, -1.0, 0.0)
    for b in np.arange(1.0, 3.01, 0.05):
        w = [b, b, 1.0, 1.0, 1.0]
        pred = decide(proba, w)
        rec, f1 = hb_recall(y, pred), macro_f1(y, pred)
        if rec >= MIN_REC_ABS + REC_MARGIN and f1 > best[1]:
            best = (w, f1, rec)
    if best[0] is None:
        for b in np.arange(1.0, 4.01, 0.05):
            w = [b, b, 1.0, 1.0, 1.0]
            rec = hb_recall(y, decide(proba, w))
            if rec > best[2]:
                best = (w, macro_f1(y, decide(proba, w)), rec)
    return list(best[0]), best[1], best[2]


# ───────────────────────────────────────── 모델별 fold 학습기
def fit_predict(name, Xtr, ytr, Xva, ncat):
    """fold 하나를 학습하고 검증 부분의 클래스 확률을 돌려준다."""
    if name == 'logit':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        A, B = enc.fit_transform(Xtr), enc.transform(Xva)
        m = LogisticRegression(max_iter=2000, random_state=SEED)
        m.fit(A, ytr)
        return m.predict_proba(B), m.classes_
    if name == 'rf':
        m = RandomForestClassifier(n_estimators=180, max_depth=14, min_samples_leaf=8,
                                   max_features='sqrt', random_state=SEED, n_jobs=-1)
    elif name == 'et':
        m = ExtraTreesClassifier(n_estimators=180, max_depth=16, min_samples_leaf=8,
                                 max_features='sqrt', random_state=SEED, n_jobs=-1)
    elif name == 'histgb':
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
                                           max_leaf_nodes=15, min_samples_leaf=20,
                                           l2_regularization=1.0, random_state=SEED,
                                           categorical_features=list(range(ncat)))
    elif name == 'lgbm':
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=15,
                               min_child_samples=25, reg_lambda=1.0, subsample=0.9,
                               colsample_bytree=0.9, random_state=SEED, n_jobs=-1,
                               verbose=-1)
        m.fit(Xtr, ytr, categorical_feature=list(range(ncat)))
        return m.predict_proba(Xva), m.classes_
    elif name == 'xgb':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        A, B = enc.fit_transform(Xtr), enc.transform(Xva)
        m = xgb.XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=4,
                              min_child_weight=5, subsample=0.9, colsample_bytree=0.9,
                              reg_lambda=1.0, random_state=SEED, n_jobs=-1,
                              tree_method='hist', eval_metric='mlogloss')
        m.fit(A, ytr - 1)
        return m.predict_proba(B), np.array(CLASSES)
    elif name == 'catboost':
        m = CatBoostClassifier(iterations=400, learning_rate=0.06, depth=5, l2_leaf_reg=3.0,
                               random_seed=SEED, verbose=0, allow_writing_files=False,
                               cat_features=list(range(ncat)))
        m.fit(Xtr.astype(int), ytr)
        return m.predict_proba(Xva.astype(int)), m.classes_
    else:
        raise ValueError(name)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xva), m.classes_


def align(proba, classes):
    """클래스 순서를 1~5 로 맞춘다."""
    out = np.zeros((proba.shape[0], 5))
    for j, c in enumerate(classes):
        out[:, CLASSES.index(int(c))] = proba[:, j]
    return out


def oof_proba(name, X, y, folds, ncat):
    P = np.zeros((len(y), 5))
    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        p, cls = fit_predict(name, X[tr], y[tr], X[va], ncat)
        P[va] = align(p, cls)
    return P


def score(P, y, label):
    """가중치 없이(argmax) 와 가중치 튜닝 후를 함께 낸다."""
    plain = decide(P)
    w, f1w, recw = tune_weights(P, y)
    pw = decide(P, w)
    return {
        'model': label,
        'macro_f1_argmax': round(macro_f1(y, plain), 4),
        'hb_recall_argmax': round(hb_recall(y, plain), 4),
        'accuracy_argmax': round(float(accuracy_score(y, plain)), 4),
        'weights': [round(v, 2) for v in w],
        'macro_f1_weighted': round(f1w, 4),
        'hb_recall_weighted': round(recw, 4),
        'accuracy_weighted': round(float(accuracy_score(y, pw)), 4),
        'binary_accuracy': round(float((( pw <= 2) == (np.asarray(y) <= 2)).mean()), 4),
    }


def main():
    d = dbmod.load_dataset(missing_sentinel=MISSING)
    feats, X, y, folds = d['features'], d['X'], d['y'], d['folds']
    sel = json.loads((ROOT / 'models' / 'selection_v1.json').read_text())['selected']
    idx = [feats.index(f) for f in sel]

    SETS = {'qs-v1.0.0 (7문항)': (X[:, idx], sel),
            '전체 38변수': (X, feats)}
    NAMES = ['logit', 'rf', 'et', 'histgb', 'lgbm', 'xgb', 'catboost']

    result = {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'note': 'train 2,398건 · DB 고정 cv_fold 5-fold OOF. test 602건 미사용.',
              'sets': {}}

    for sname, (Xs, cols) in SETS.items():
        print(f'\n===== {sname} ({Xs.shape[1]}변수) =====', flush=True)
        ncat = Xs.shape[1]
        probas, rows = {}, []
        for n in NAMES:
            t0 = time.time()
            P = oof_proba(n, Xs, y, folds, ncat)
            probas[n] = P
            r = score(P, y, n)
            r['fit_sec'] = round(time.time() - t0, 1)
            rows.append(r)
            print(f"  {n:9} F1(w)={r['macro_f1_weighted']:.4f} "
                  f"고부담재현율={r['hb_recall_weighted']:.4f} "
                  f"정확도={r['accuracy_weighted']:.4f} ({r['fit_sec']}s)", flush=True)

        # ── 앙상블 1: 소프트 보팅 (전 계열 평균)
        rows.append(score(np.mean([probas[n] for n in NAMES], axis=0), y,
                          'ensemble:soft-vote(전체 7종)'))
        # ── 앙상블 2: 로지스틱 + 부스팅 3종
        pick = ['logit', 'lgbm', 'xgb', 'catboost']
        rows.append(score(np.mean([probas[n] for n in pick], axis=0), y,
                          'ensemble:soft-vote(logit+부스팅3)'))
        # ── 앙상블 3: 로지스틱 + LightGBM 만
        rows.append(score(np.mean([probas['logit'], probas['lgbm']], axis=0), y,
                          'ensemble:soft-vote(logit+lgbm)'))
        # ── 앙상블 4: 스태킹 (OOF 확률 → 로지스틱 메타)
        Z = np.hstack([probas[n] for n in NAMES])
        Pm = np.zeros((len(y), 5))
        for k in sorted(set(folds)):
            tr, va = folds != k, folds == k
            meta = LogisticRegression(max_iter=2000, random_state=SEED)
            meta.fit(Z[tr], y[tr])
            Pm[va] = align(meta.predict_proba(Z[va]), meta.classes_)
        rows.append(score(Pm, y, 'ensemble:stacking(메타=로지스틱)'))

        for r in rows[len(NAMES):]:
            print(f"  {r['model']:34} F1(w)={r['macro_f1_weighted']:.4f} "
                  f"고부담재현율={r['hb_recall_weighted']:.4f} "
                  f"정확도={r['accuracy_weighted']:.4f}", flush=True)
        result['sets'][sname] = {'n_features': int(Xs.shape[1]), 'columns': list(cols),
                                 'rows': rows}

    out = ROOT / 'docs' / 'SJH-모델비교-결과.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n저장: {out}')


if __name__ == '__main__':
    main()
