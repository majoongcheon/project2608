"""단계들이 공유하는 계산. ml/train.py 에서 그대로 옮겼다.

옮기면서 바꾼 것은 **모듈 전역 상수를 config 에서 읽게 한 것**뿐이다.
계산 자체는 손대지 않았다 — 바꾸면 같은 데이터에서 다른 모델이 나온다.
"""
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.preprocessing import OneHotEncoder

from cb_burden import config

CLASSES = config.CLASSES
SEED = config.SEED
MIN_REC_ABS = config.SUCCESS_CRITERIA['min_recall_abs']
REC_MARGIN = config.REC_MARGIN


def train_view(snap):
    """스냅샷에서 train 부분만 꺼낸다.

    원본 db.load_dataset 은 train/test 를 따로 줬다. 스냅샷은 한 배열에 담고 split 으로
    구분하므로, 단계 함수가 원본과 같은 모양의 입력을 받도록 여기서 잘라 준다.
    """
    m = snap['split'] == 'train'
    return snap['X'][m], snap['y'][m], snap['cv_fold'][m]


def test_view(snap):
    m = snap['split'] == 'test'
    return snap['X'][m], snap['y'][m]


def macro_f1(y, p):
    return float(f1_score(y, p, average='macro', labels=CLASSES, zero_division=0))


def high_burden_recall(y, p):
    """실제 고부담(1~2)인 사람 중 시스템도 고부담으로 판정한 비율 (SC-005)."""
    y, p = np.asarray(y), np.asarray(p)
    actual = (y <= 2)
    if actual.sum() == 0:
        return 0.0
    return float(((p <= 2) & actual).sum() / actual.sum())


def decide(proba, weights=None):
    """확률에서 최종 구간을 고른다.

    고부담(1~2)을 놓치는 것이 이 서비스에서 가장 비싼 오류이므로(SC-005),
    단순 argmax 가 아니라 **구간별 결정 가중치**를 곱해 고른다.
    """
    p = np.asarray(proba, dtype=float)
    if weights is not None:
        p = p * np.asarray(weights, dtype=float)
    return np.asarray(CLASSES)[p.argmax(axis=1)]


def tune_decision_weights(proba, y):
    """고부담 재현율 하한을 만족하는 가중치 중 macro F1 이 가장 높은 것을 고른다."""
    best = (None, -1.0, 0.0)
    for boost in np.arange(1.0, 3.01, 0.05):
        w = [boost, boost, 1.0, 1.0, 1.0]
        pred = decide(proba, w)
        rec = high_burden_recall(y, pred)
        f1 = macro_f1(y, pred)
        if rec >= MIN_REC_ABS + REC_MARGIN and f1 > best[1]:
            best = (w, f1, rec)
    if best[0] is None:                     # 하한을 못 맞추면 재현율이 가장 높은 쪽
        for boost in np.arange(1.0, 4.01, 0.05):
            w = [boost, boost, 1.0, 1.0, 1.0]
            rec = high_burden_recall(y, decide(proba, w))
            if rec > best[2]:
                best = (w, macro_f1(y, decide(proba, w)), rec)
    return list(best[0]), {'macro_f1': best[1], 'high_burden_recall': best[2]}


def make_model(family):
    if family == 'rf':
        return RandomForestClassifier(
            n_estimators=180, max_depth=14, min_samples_leaf=8, max_features='sqrt',
            class_weight=None, random_state=SEED, n_jobs=-1)
    if family == 'et':
        return ExtraTreesClassifier(
            n_estimators=180, max_depth=16, min_samples_leaf=8, max_features='sqrt',
            class_weight=None, random_state=SEED, n_jobs=-1)
    if family == 'logit':
        return 'logit'
    raise ValueError(family)


def cv_scores(X, y, folds, features, family='rf', want_importance=False, weights=None):
    """cv_fold 로 고정된 5-fold 교차검증. 분할을 새로 만들지 않는다(원칙 IV)."""
    f1s, recs = [], []
    imp = np.zeros(len(features))
    oof_proba = np.zeros((len(y), len(CLASSES)))
    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        if family == 'logit':
            enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
            Xtr, Xva = enc.fit_transform(X[tr]), enc.transform(X[va])
            m = LogisticRegression(max_iter=2000, random_state=SEED)
            m.fit(Xtr, y[tr])
            proba = m.predict_proba(Xva)
            pred = decide(proba, weights)
            if want_importance:
                # 변수 하나가 차지하는 원-핫 열들의 |계수| 평균을 그 변수의 중요도로 본다
                col = 0
                for j, cats in enumerate(enc.categories_):
                    w_abs = np.abs(m.coef_[:, col:col + len(cats)])
                    imp[j] += float(w_abs.mean())
                    col += len(cats)
        else:
            m = make_model(family)
            m.fit(X[tr], y[tr])
            proba = m.predict_proba(X[va])
            pred = decide(proba, weights)
            if want_importance:
                imp += m.feature_importances_
        f1s.append(macro_f1(y[va], pred))
        recs.append(high_burden_recall(y[va], pred))
        oof_proba[va] = proba
    out = {'macro_f1': float(np.mean(f1s)), 'high_burden_recall': float(np.mean(recs))}
    if want_importance:
        out['importance'] = imp / len(set(folds))
    out['oof_proba'] = oof_proba
    return out


def build_freq_table(X, features):
    """변수별 응답 범주 빈도. 개별 행이 아니라 집계값이라 런타임에 두어도 안전하다."""
    table = {}
    n = len(X)
    for j, f in enumerate(features):
        vals, counts = np.unique(X[:, j], return_counts=True)
        table[f] = {str(int(v)): float(c / n) for v, c in zip(vals, counts)}
    return table


def rarity(row, features, table, eps=1e-4):
    """응답 조합이 학습 데이터에서 얼마나 드문가. 작을수록(음수로 클수록) 드물다."""
    s = 0.0
    for j, f in enumerate(features):
        p = table[f].get(str(int(row[j])), eps)
        s += np.log(max(p, eps))
    return float(s / len(features))
