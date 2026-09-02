# -*- coding: utf-8 -*-
"""CHJ-01 · 앙상블이 정말 진 것인가 (최호준).

물음 하나에만 답한다 — **앙상블이 단일 로지스틱보다 낮은 것이 실제 차이인가, 잡음인가.**
성능을 올리려는 실험이 아니다. 차이의 크기와 그 불확실성을 재는 실험이다.

배포 파이프라인(ml/train.py)을 건드리지 않는 읽기 전용 실험이다.
models/ 에 아무것도 쓰지 않고, 결과는 docs/CHJ-앙상블비교-결과.json 으로만 남긴다.
기존 벤치마크 결과(docs/SJH-모델비교-결과.json)는 읽지 않는다 — 기준선도 여기서 다시 잰다.

★ test 602건은 절대 사용하지 않는다. train 2,398건만 쓴다.

기존 벤치마크와 다른 점 세 가지
  1. 클래스 가중치를 fold 의 **학습 부분에서만** 고르고 검증 부분에 적용한다.
     (기존은 OOF 전체에서 고른 가중치를 같은 OOF 에서 채점 → 모델마다 크기가 다른 낙관 편향)
  2. 스태킹 메타와 혼합 가중치도 같은 규칙으로 내부 CV 안에서만 학습한다.
  3. 점수 하나가 아니라 **짝지은 차이와 두 종류의 구간**을 낸다.
     - 반복 CV → 분할을 바꾸면 얼마나 흔들리는가 (분할 잡음)
     - 행 부트스트랩 → 다른 2,398가구였다면 얼마나 달랐겠는가 (표본 잡음)

  python3 ml/CHJ-ensemble-compare.py                 # 5회 반복, 약 30~40분
  python3 ml/CHJ-ensemble-compare.py --repeats 2     # 빠른 확인
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in ('ml/.pylibs-sjh', 'ml/.pylibs', 'ml'):
    sys.path.insert(0, str(ROOT / p))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import StratifiedKFold
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

import db as dbmod

SEED = 20260902
CLASSES = [1, 2, 3, 4, 5]
MISSING = -1

# 판정 규칙 — care_burden 은 1이 최고부담인 역방향 척도라 고부담은 <= 2 다.
HIGH_BURDEN = 2
MIN_REC_ABS, REC_MARGIN = 0.70, 0.03   # train.py 와 같은 가중치 선택 규칙

BASE_MODELS = ['logit', 'rf', 'lgbm', 'xgb', 'catboost']
BASELINE = 'logit'                      # 현 배포본 v1.0.0 이 기준선이다
ENSEMBLES = ['soft_all', 'soft_lin_boost', 'soft_weighted', 'stacking']
SOFT_LIN_BOOST = ['logit', 'lgbm', 'xgb', 'catboost']

LABELS = {
    'logit': 'logit (배포본 v1.0.0)',
    'rf': 'rf',
    'lgbm': 'lgbm',
    'xgb': 'xgb',
    'catboost': 'catboost',
    'soft_all': '앙상블: 소프트보팅(5종)',
    'soft_lin_boost': '앙상블: 소프트보팅(선형+부스팅3)',
    'soft_weighted': '앙상블: 가중 소프트보팅(내부CV 학습)',
    'stacking': '앙상블: 스태킹(메타=로지스틱)',
}


# ───────────────────────────────────────────────────────── 지표
NC = len(CLASSES)
HB = HIGH_BURDEN            # 혼동행렬에서 고부담은 앞의 2행·2열이다 (역방향 척도)


def confusion(y, p):
    """C[i, j] = 실제 i+1 을 j+1 로 판정한 수. bincount 한 번으로 센다."""
    idx = (np.asarray(y) - 1) * NC + (np.asarray(p) - 1)
    return np.bincount(idx, minlength=NC * NC).reshape(NC, NC)


def metrics_from_confusion(C):
    """부트스트랩이 수만 번 부르는 자리라 sklearn 대신 행렬에서 직접 뽑는다."""
    n = C.sum()
    tp = np.diag(C).astype(float)
    fp = C.sum(axis=0) - tp
    fn = C.sum(axis=1) - tp
    denom = 2 * tp + fp + fn
    f1 = np.divide(2 * tp, denom, out=np.zeros(NC), where=denom > 0)

    hb_tp = float(C[:HB, :HB].sum())
    hb_fn = float(C[:HB, HB:].sum())
    hb_fp = float(C[HB:, :HB].sum())
    hb_tn = float(C[HB:, HB:].sum())
    rec = hb_tp / (hb_tp + hb_fn) if (hb_tp + hb_fn) else 0.0
    prec = hb_tp / (hb_tp + hb_fp) if (hb_tp + hb_fp) else 0.0
    return {
        'macro_f1': float(f1.mean()),
        'hb_recall': rec,
        'hb_precision': prec,
        'hb_f1': (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0,
        'binary_accuracy': (hb_tp + hb_tn) / n if n else 0.0,
        'accuracy': float(tp.sum() / n) if n else 0.0,
    }


def metrics(y, p):
    return metrics_from_confusion(confusion(y, p))


def macro_f1(y, p):
    return metrics(y, p)['macro_f1']


def hb_recall(y, p):
    """고부담(1~2)을 고부담으로 판정한 비율. 놓친 보호자의 반대말이다."""
    return metrics(y, p)['hb_recall']


METRIC_KEYS = ['macro_f1', 'hb_recall', 'hb_precision', 'hb_f1', 'binary_accuracy', 'accuracy']


def decide(proba, w=None):
    p = np.asarray(proba, float)
    if w is not None:
        p = p * np.asarray(w, float)
    return np.asarray(CLASSES)[p.argmax(axis=1)]


def tune_class_weights(proba, y):
    """고부담 쪽으로 미는 클래스 배수를 고른다. train.py 와 같은 규칙.

    ★ 반드시 fold 의 학습 부분에서만 부른다. 검증 부분을 보고 고르면 편향이 생긴다.
    """
    best_w, best_f1, best_rec = None, -1.0, -1.0
    for b in np.arange(1.0, 3.01, 0.05):
        w = [b, b, 1.0, 1.0, 1.0]
        pred = decide(proba, w)
        rec, f1 = hb_recall(y, pred), macro_f1(y, pred)
        if rec >= MIN_REC_ABS + REC_MARGIN and f1 > best_f1:
            best_w, best_f1, best_rec = w, f1, rec
    if best_w is None:                    # 목표 재현율에 못 닿으면 재현율 최대로
        for b in np.arange(1.0, 4.01, 0.05):
            w = [b, b, 1.0, 1.0, 1.0]
            rec = hb_recall(y, decide(proba, w))
            if rec > best_rec:
                best_w, best_rec = w, rec
    return list(best_w)


# ───────────────────────────────────────────────── 모델 한 판 학습
def fit_predict(name, Xtr, ytr, Xva, ncat):
    """fold 하나를 학습하고 검증 부분의 1~5 클래스 확률을 돌려준다."""
    if name == 'logit':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        A, B = enc.fit_transform(Xtr), enc.transform(Xva)
        m = LogisticRegression(max_iter=2000, random_state=SEED)
        m.fit(A, ytr)
        return align(m.predict_proba(B), m.classes_)
    if name == 'rf':
        m = RandomForestClassifier(n_estimators=180, max_depth=14, min_samples_leaf=8,
                                   max_features='sqrt', random_state=SEED, n_jobs=-1)
        m.fit(Xtr, ytr)
        return align(m.predict_proba(Xva), m.classes_)
    if name == 'lgbm':
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=15,
                               min_child_samples=25, reg_lambda=1.0, subsample=0.9,
                               colsample_bytree=0.9, random_state=SEED, n_jobs=-1, verbose=-1)
        m.fit(Xtr, ytr, categorical_feature=list(range(ncat)))
        return align(m.predict_proba(Xva), m.classes_)
    if name == 'xgb':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        A, B = enc.fit_transform(Xtr), enc.transform(Xva)
        m = xgb.XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=4,
                              min_child_weight=5, subsample=0.9, colsample_bytree=0.9,
                              reg_lambda=1.0, random_state=SEED, n_jobs=-1,
                              tree_method='hist', eval_metric='mlogloss')
        m.fit(A, ytr - 1)
        return align(m.predict_proba(B), np.array(CLASSES))
    if name == 'catboost':
        m = CatBoostClassifier(iterations=400, learning_rate=0.06, depth=5, l2_leaf_reg=3.0,
                               random_seed=SEED, verbose=0, allow_writing_files=False,
                               cat_features=list(range(ncat)))
        m.fit(Xtr.astype(int), ytr)
        return align(m.predict_proba(Xva.astype(int)), m.classes_)
    raise ValueError(name)


def align(proba, classes):
    """클래스 순서를 1~5 로 맞춘다. 모델마다 순서가 달라 반드시 거쳐야 한다."""
    out = np.zeros((proba.shape[0], len(CLASSES)))
    for j, c in enumerate(classes):
        out[:, CLASSES.index(int(c))] = proba[:, j]
    return out


def base_probas(Xtr, ytr, Xva, ncat):
    return {n: fit_predict(n, Xtr, ytr, Xva, ncat) for n in BASE_MODELS}


def inner_oof(Xtr, ytr, ncat, n_splits, seed):
    """학습 부분 안에서만 도는 내부 CV. 혼합 가중치·메타·클래스 배수를 여기서만 배운다."""
    P = {n: np.zeros((len(ytr), len(CLASSES))) for n in BASE_MODELS}
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for a, b in skf.split(Xtr, ytr):
        got = base_probas(Xtr[a], ytr[a], Xtr[b], ncat)
        for n in BASE_MODELS:
            P[n][b] = got[n]
    return P


# ───────────────────────────────────────────────────── 앙상블 결합
def soft_vote(probas, names, weights=None):
    stack = np.stack([probas[n] for n in names])          # (모델, 행, 클래스)
    if weights is None:
        return stack.mean(axis=0)
    w = np.asarray(weights, float).reshape(-1, 1, 1)
    return (stack * w).sum(axis=0) / w.sum()


def search_blend_weights(probas, y, rng, n_draw=200):
    """모델별 혼합 비율을 무작위 탐색으로 고른다. 내부 OOF 에서만 부른다."""
    best_w, best_f1 = np.ones(len(BASE_MODELS)) / len(BASE_MODELS), -1.0
    draws = np.vstack([best_w, rng.dirichlet(np.ones(len(BASE_MODELS)), size=n_draw)])
    for w in draws:
        f1 = macro_f1(y, decide(soft_vote(probas, BASE_MODELS, w)))
        if f1 > best_f1:
            best_w, best_f1 = w, f1
    return list(map(float, best_w))


def stack_matrix(probas):
    return np.hstack([probas[n] for n in BASE_MODELS])    # 5모델 × 5클래스 = 25열


def fit_meta(probas, y):
    m = LogisticRegression(max_iter=2000, random_state=SEED)
    m.fit(stack_matrix(probas), y)
    return m


def meta_oof(probas, y, n_splits, seed):
    """메타의 클래스 배수를 고르기 위한, 메타 자신의 내부 OOF."""
    Z, out = stack_matrix(probas), np.zeros((len(y), len(CLASSES)))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for a, b in skf.split(Z, y):
        m = LogisticRegression(max_iter=2000, random_state=SEED)
        m.fit(Z[a], y[a])
        out[b] = align(m.predict_proba(Z[b]), m.classes_)
    return out


# ─────────────────────────────────────────────── 반복 1회 = 바깥 5-fold
def run_repeat(X, y, folds, ncat, inner_splits, seed, tag):
    """바깥 fold 를 돌며 각 구성의 검증부분 판정을 모은다. 학습 부분만 보고 모든 것을 정한다."""
    names = BASE_MODELS + ENSEMBLES
    pred = {n: np.zeros(len(y), dtype=int) for n in names}
    rng = np.random.default_rng(seed)

    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        Xtr, ytr, Xva = X[tr], y[tr], X[va]
        t0 = time.time()

        outer = base_probas(Xtr, ytr, Xva, ncat)          # 검증 부분 확률
        inner = inner_oof(Xtr, ytr, ncat, inner_splits, seed + k)   # 학습 부분 내부 OOF

        # 단일 모델 — 클래스 배수를 내부 OOF 에서 고르고 검증 부분에 적용
        for n in BASE_MODELS:
            pred[n][va] = decide(outer[n], tune_class_weights(inner[n], ytr))

        # 앙상블 1·2 — 단순 평균
        for cfg, members in (('soft_all', BASE_MODELS), ('soft_lin_boost', SOFT_LIN_BOOST)):
            w = tune_class_weights(soft_vote(inner, members), ytr)
            pred[cfg][va] = decide(soft_vote(outer, members), w)

        # 앙상블 3 — 혼합 비율도 내부 OOF 에서 학습
        blend = search_blend_weights(inner, ytr, rng)
        w = tune_class_weights(soft_vote(inner, BASE_MODELS, blend), ytr)
        pred['soft_weighted'][va] = decide(soft_vote(outer, BASE_MODELS, blend), w)

        # 앙상블 4 — 메타를 내부 OOF 로 학습(누수 차단), 배수는 메타의 내부 OOF 에서
        meta = fit_meta(inner, ytr)
        w = tune_class_weights(meta_oof(inner, ytr, inner_splits, seed + k), ytr)
        pred['stacking'][va] = decide(align(meta.predict_proba(stack_matrix(outer)),
                                            meta.classes_), w)

        print(f'    fold {k} 완료 ({time.time() - t0:.0f}s)', flush=True)

    scores = {n: metrics(y, pred[n]) for n in names}
    print(f'  [{tag}] ' + ' · '.join(
        f"{n}={scores[n]['macro_f1']:.4f}" for n in (BASELINE, 'soft_all', 'stacking')), flush=True)
    return scores, pred


# ──────────────────────────────────────────────────────── 차이와 구간
def t_interval(diffs, conf=0.95):
    """반복 간 차이의 평균과 구간. 반복 수가 적어 t 분포를 쓴다."""
    d = np.asarray(diffs, float)
    n = len(d)
    mean = float(d.mean())
    if n < 2:
        return mean, None, None
    se = float(d.std(ddof=1) / np.sqrt(n))
    # t 임계값 (양측 95%), 자유도 1~9 표
    tcrit = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
             6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}.get(n - 1, 1.96)
    return mean, mean - tcrit * se, mean + tcrit * se


def bootstrap_diffs(y, pred_a, pred_b, boot_idx):
    """같은 행에서 두 구성의 차이를 재표본한다. 모델을 다시 학습하지 않는다.

    반복 CV 구간이 '분할을 바꾸면'이라면, 이쪽은 '다른 2,398가구였다면'에 답한다.
    재표본 색인은 모든 구성이 공유한다 — 그래야 비교가 짝지어진다.
    """
    y, a, b = np.asarray(y), np.asarray(pred_a), np.asarray(pred_b)
    diffs = {k: np.empty(len(boot_idx)) for k in METRIC_KEYS}
    for i, idx in enumerate(boot_idx):
        ma = metrics_from_confusion(confusion(y[idx], a[idx]))
        mb = metrics_from_confusion(confusion(y[idx], b[idx]))
        for k in METRIC_KEYS:
            diffs[k][i] = ma[k] - mb[k]
    return {k: (float(v.mean()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
            for k, v in diffs.items()}


def verdict(lo, hi):
    """구간이 0을 품으면 차이를 주장하지 않는다."""
    if lo is None:
        return '반복 부족'
    if lo > 0:
        return '기준선보다 높음'
    if hi < 0:
        return '기준선보다 낮음'
    return '차이 없음 (잡음)'


# ──────────────────────────────────────────────────────────────── 실행
def main():
    global BASE_MODELS, SOFT_LIN_BOOST
    ap = argparse.ArgumentParser()
    ap.add_argument('--repeats', type=int, default=5, help='반복 CV 횟수 (1회차는 DB 고정 fold)')
    ap.add_argument('--inner-splits', type=int, default=3, help='내부 CV 겹 수')
    ap.add_argument('--bootstrap', type=int, default=2000, help='행 부트스트랩 재표본 수')
    ap.add_argument('--models', default=','.join(BASE_MODELS),
                    help='기본 모델 목록. 배선 점검용으로 줄여 돌릴 때만 쓴다')
    ap.add_argument('--out', default='docs/CHJ-앙상블비교-결과.json')
    args = ap.parse_args()

    chosen = [m.strip() for m in args.models.split(',') if m.strip()]
    unknown = set(chosen) - set(BASE_MODELS)
    assert not unknown, f'모르는 모델: {unknown}'
    assert BASELINE in chosen, f'기준선 {BASELINE} 이 빠졌다'
    BASE_MODELS = chosen
    SOFT_LIN_BOOST = [m for m in SOFT_LIN_BOOST if m in chosen]

    d = dbmod.load_dataset(missing_sentinel=MISSING)
    feats, X, y, db_folds = d['features'], d['X'], d['y'], d['folds']
    # ★ d['Xtest'] · d['ytest'] 는 이 파일 어디에서도 쓰지 않는다.

    sel = json.loads((ROOT / 'models' / 'selection_v1.json').read_text())['selected']
    Xs = X[:, [feats.index(f) for f in sel]]
    ncat = Xs.shape[1]

    print(f'train {len(y)}건 · 7문항 {sel}')
    print(f'고부담(1~2) {int((y <= HIGH_BURDEN).sum())}건 ({(y <= HIGH_BURDEN).mean():.3f})')
    print(f'반복 {args.repeats}회 · 내부 {args.inner_splits}겹 · 부트스트랩 {args.bootstrap}회\n')

    all_scores, keep_pred = [], None
    for r in range(args.repeats):
        if r == 0:
            folds, how = db_folds, 'DB 고정 cv_fold'
        else:
            folds = np.zeros(len(y), dtype=int)
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED + r)
            for i, (_, va) in enumerate(skf.split(Xs, y), start=1):
                folds[va] = i
            how = f'층화 5-fold (seed {SEED + r})'
        print(f'── 반복 {r + 1}/{args.repeats} — {how}', flush=True)
        t0 = time.time()
        scores, pred = run_repeat(Xs, y, folds, ncat, args.inner_splits, SEED + r * 100, f'반복{r + 1}')
        print(f'  ({time.time() - t0:.0f}s)\n', flush=True)
        all_scores.append({'repeat': r + 1, 'folds': how, 'scores': scores})
        if r == 0:
            keep_pred = pred          # 부트스트랩은 재현 가능한 DB 고정 분할에서만 한다

    # ── 구성별 평균
    names = BASE_MODELS + ENSEMBLES
    summary = {}
    for n in names:
        summary[n] = {'label': LABELS[n]}
        for k in METRIC_KEYS:
            vals = [s['scores'][n][k] for s in all_scores]
            summary[n][k] = {'mean': round(float(np.mean(vals)), 4),
                             'sd': round(float(np.std(vals, ddof=1)), 4) if len(vals) > 1 else None,
                             'per_repeat': [round(v, 4) for v in vals]}

    # ── 기준선(배포본)과의 짝지은 차이
    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, len(y), size=(args.bootstrap, len(y)))
    comparisons = []
    for n in names:
        if n == BASELINE:
            continue
        boot = bootstrap_diffs(y, keep_pred[n], keep_pred[BASELINE], boot_idx)
        entry = {'config': n, 'label': LABELS[n], 'vs': LABELS[BASELINE], 'metrics': {}}
        for k in METRIC_KEYS:
            diffs = [s['scores'][n][k] - s['scores'][BASELINE][k] for s in all_scores]
            m, lo, hi = t_interval(diffs)
            bm, blo, bhi = boot[k]
            entry['metrics'][k] = {
                'repeat_mean_diff': round(m, 4),
                'repeat_ci95': [round(lo, 4), round(hi, 4)] if lo is not None else None,
                'repeat_verdict': verdict(lo, hi),
                'boot_mean_diff': round(bm, 4),
                'boot_ci95': [round(blo, 4), round(bhi, 4)],
                'boot_verdict': verdict(blo, bhi),
            }
        comparisons.append(entry)

    result = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'author': '최호준 (CHJ)',
        'question': '앙상블이 단일 로지스틱보다 낮은 것이 실제 차이인가, 잡음인가',
        'note': ('train 2,398건만 사용. test 602건 미사용. '
                 '클래스 배수·혼합 가중치·스태킹 메타를 모두 fold 학습 부분의 내부 CV 에서만 학습했다.'),
        'setup': {'n_train': int(len(y)), 'question_set': 'qs-v1.0.0', 'features': sel,
                  'high_burden_rate': round(float((y <= HIGH_BURDEN).mean()), 4),
                  'repeats': args.repeats, 'inner_splits': args.inner_splits,
                  'bootstrap': args.bootstrap, 'baseline': BASELINE},
        'summary': summary,
        'comparisons': comparisons,
        'per_repeat': all_scores,
    }
    out = ROOT / args.out
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── 화면 요약
    print('=' * 78)
    print(f"{'구성':38} {'macroF1':>9} {'고부담재현':>10} {'고부담F1':>9}")
    for n in names:
        s = summary[n]
        mark = ' ←기준선' if n == BASELINE else ''
        print(f"{LABELS[n]:38} {s['macro_f1']['mean']:9.4f} "
              f"{s['hb_recall']['mean']:10.4f} {s['hb_f1']['mean']:9.4f}{mark}")
    print('\n' + '=' * 78)
    print(f'{LABELS[BASELINE]} 과의 차이 — macro F1')
    for c in comparisons:
        m = c['metrics']['macro_f1']
        ci = m['repeat_ci95']
        cis = f"[{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else '(구간 없음)'
        bci = m['boot_ci95']
        print(f"  {c['label']:38} {m['repeat_mean_diff']:+.4f} {cis:>22}  {m['repeat_verdict']}")
        print(f"  {'':38} {m['boot_mean_diff']:+.4f} "
              f"{f'[{bci[0]:+.4f}, {bci[1]:+.4f}]':>22}  {m['boot_verdict']} (행 부트스트랩)")
    print(f'\n저장: {out}')


if __name__ == '__main__':
    main()
