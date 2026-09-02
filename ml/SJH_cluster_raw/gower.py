# -*- coding: utf-8 -*-
"""Gower 거리 — 혼합형 데이터를 위한 거리.

왜 유클리드가 아닌가 — 이 데이터는 binary·nominal·ordinal·continuous 가 섞여 있다.
전부 원-핫으로 펴서 유클리드를 쓰면 순서형의 순서가 사라지고, 레벨 수가 많은 변수가
총 분산을 지배한다. Gower 는 변수 유형별로 다른 거리를 쓰고 각각 [0,1] 로 정규화한
뒤 가중 평균한다.

    d(i,j) = Σ w_k · d_k(i,j) / Σ w_k        (둘 다 응답한 변수 k 에 대해서만)

결측은 **쌍 단위로 제외**한다(pairwise deletion). 분기 결측은 "해당 없음"이므로,
비교할 수 없는 문항을 억지로 0 이나 1 로 채우지 않는다.

메모리 — n=2,398 이면 (n,n) float32 가 23MB. 변수마다 임시 행렬 하나를 쓰므로
동시 사용량은 100MB 정도다.
"""
import numpy as np


def block_weights(columns, column_block):
    """같은 블록에 딸린 문항들이 합쳐서 1표가 되도록 가중치를 만든다.

    column_block: {컬럼: 블록이름}. 블록이 없는 컬럼은 1.0.

    왜 필요한가 — 취업 블록 52문항을 각각 1표로 두면 "취업 경험 없음"이라는 사실
    하나가 52표를 갖는다. 블록당 기여를 같게 맞춘다.
    """
    counts = {}
    for c in columns:
        b = column_block.get(c)
        if b is not None:
            counts[b] = counts.get(b, 0) + 1
    return [1.0 / counts[column_block[c]] if column_block.get(c) else 1.0
            for c in columns]


def distance(X, kinds, weights=None):
    """(n, p) 실수 배열에서 (n, n) Gower 거리 행렬을 만든다.

    X      결측은 np.nan. nominal·binary 도 숫자 코드로 넣는다.
    kinds  각 열의 척도 — 'binary' | 'nominal' | 'ordinal' | 'continuous'
    """
    X = np.asarray(X, dtype=np.float64)
    n, p = X.shape
    if weights is None:
        weights = [1.0] * p
    if len(kinds) != p or len(weights) != p:
        raise ValueError(f'열 수와 맞지 않는다: p={p} kinds={len(kinds)} w={len(weights)}')

    num = np.zeros((n, n), dtype=np.float32)
    den = np.zeros((n, n), dtype=np.float32)

    for k in range(p):
        x = X[:, k]
        ok = ~np.isnan(x)
        pair = (ok[:, None] & ok[None, :])
        if not pair.any():
            continue

        if kinds[k] in ('ordinal', 'continuous'):
            lo, hi = np.nanmin(x), np.nanmax(x)
            rng = hi - lo
            if rng <= 0:
                d = np.zeros((n, n), dtype=np.float32)
            else:
                xf = np.where(ok, x, 0.0)
                d = (np.abs(xf[:, None] - xf[None, :]) / rng).astype(np.float32)
        else:                                   # binary · nominal
            xf = np.where(ok, x, 0.0)
            d = (xf[:, None] != xf[None, :]).astype(np.float32)

        w = np.float32(weights[k])
        num += w * np.where(pair, d, np.float32(0.0))
        den += w * pair.astype(np.float32)

    # 비교 가능한 변수가 하나도 없는 쌍은 최대 거리로 둔다.
    # 임의로 0(가깝다)으로 두면 군집이 결측 때문에 뭉친다.
    out = np.ones((n, n), dtype=np.float32)
    has = den > 0
    np.divide(num, den, out=out, where=has)
    np.fill_diagonal(out, 0.0)
    return np.clip((out + out.T) / 2.0, 0.0, 1.0)
