# -*- coding: utf-8 -*-
"""추론과 기여도 산출 — TS 구현(backend/src/inference)의 **기준 구현**.

두 계열을 지원한다. 어느 쪽이든 `sum(contributions) + base = score` 가 정확히 성립한다.

  logit  다항 로지스틱. 기여도 = 계수 − 학습 분포에서의 기대 계수 (선형 SHAP).
         정확한 분해이며 근사가 아니다.
  rf/et  트리 앙상블. 기여도 = Saabas 경로 분해.
         research.md R-3 이 TreeSHAP 이식이 어려울 때의 승인된 폴백으로 지정한 방식이다.
         이 경우 화면에는 크기를 숫자로 표기하지 않고 순위와 강·약 구분만 쓴다.

이 파일과 backend/src/inference/*.ts 는 같은 알고리즘을 구현하며,
patiry 테스트(models/parity_v1.json)가 두 구현의 일치를 보증한다.
"""
import math


# ───────────────────────────────────────────────────────── 공통
def _softmax(z):
    m = max(z)
    e = [math.exp(v - m) for v in z]
    s = sum(e)
    return [v / s for v in e]


def decide(model, proba):
    """확률에서 최종 구간 인덱스를 고른다. 결정 가중치를 적용한다(SC-005)."""
    w = model.get('decision_weights') or [1.0] * len(proba)
    return max(range(len(proba)), key=lambda i: proba[i] * w[i])


# ───────────────────────────────────────────────── 선형 (logit)
def _cat_index(model, j, value):
    """변수 j 의 응답값이 몇 번째 범주인지. 미지의 값은 -1 (원-핫 전부 0)."""
    cats = model['categories'][j]
    for i, c in enumerate(cats):
        if c == value:
            return i
    return -1


def _logit_scores(model, row):
    nc = len(model['classes'])
    z = list(model['intercept'])
    for j in range(len(model['features'])):
        idx = _cat_index(model, j, row[j])
        if idx < 0:
            continue
        col = model['spans'][j][0] + idx
        for c in range(nc):
            z[c] += model['coef'][c][col]
    return z


def _logit_contrib(model, row, cls):
    contrib = []
    for j in range(len(model['features'])):
        idx = _cat_index(model, j, row[j])
        actual = 0.0 if idx < 0 else model['coef'][cls][model['spans'][j][0] + idx]
        contrib.append(actual - model['expected_contrib'][j][cls])
    base = model['intercept'][cls] + sum(e[cls] for e in model['expected_contrib'])
    return contrib, base


# ───────────────────────────────────────────────── 트리 (rf/et)
def _tree_leaf_path(tree, row):
    node, path, feats = 0, [0], []
    while tree['left'][node] != -1:
        f = tree['feature'][node]
        feats.append(f)
        node = tree['left'][node] if row[f] <= tree['threshold'][node] else tree['right'][node]
        path.append(node)
    return path, feats


def _tree_proba(model, row):
    trees = model['trees']
    nc = len(model['classes'])
    acc = [0.0] * nc
    for t in trees:
        node = 0
        while t['left'][node] != -1:
            f = t['feature'][node]
            node = t['left'][node] if row[f] <= t['threshold'][node] else t['right'][node]
        v = t['value'][node]
        for c in range(nc):
            acc[c] += v[c]
    return [a / len(trees) for a in acc]


def _tree_contrib(model, row, cls):
    trees = model['trees']
    contrib = [0.0] * len(model['features'])
    base = 0.0
    for t in trees:
        path, feats = _tree_leaf_path(t, row)
        base += t['value'][0][cls]
        for i, f in enumerate(feats):
            contrib[f] += t['value'][path[i + 1]][cls] - t['value'][path[i]][cls]
    n = len(trees)
    return [c / n for c in contrib], base / n


# ───────────────────────────────────────────────────────── API
def predict_proba(model, row):
    if model['family'] == 'logit':
        return _softmax(_logit_scores(model, row))
    return _tree_proba(model, row)


def contributions(model, row, cls=None):
    """(변수별 기여도, 기준값). cls 를 주지 않으면 결정된 구간을 쓴다."""
    proba = predict_proba(model, row)
    if cls is None:
        cls = decide(model, proba)
    if model['family'] == 'logit':
        return _logit_contrib(model, row, cls)
    return _tree_contrib(model, row, cls)
