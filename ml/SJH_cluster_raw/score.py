# -*- coding: utf-8 -*-
"""군집을 채점한다.

지표 하나로 단정하지 않는다. 앞선 실험은 ARI 0.027 만 보고 '부담과 무관'이라고
정리했는데, 같은 교차표에서 한 군집은 고부담 80.6%(전체 54.4% 대비 1.48배)였다.
ARI 는 '5개 라벨이 통째로 일치하는가'를 재는 엄격한 지표라 부분적인 신호를 지운다.
그래서 리프트와 교차표를 함께 본다.
"""
import numpy as np
from sklearn.metrics import (adjusted_rand_score, normalized_mutual_info_score,
                             silhouette_score)

HIGH_BURDEN = (1, 2)          # 1 최고부담군 · 2 고부담군 (역방향 척도)


def silhouette(D, labels):
    """거리 행렬 위에서 실루엣을 잰다. 군집이 하나뿐이면 정의되지 않는다."""
    if len(set(np.asarray(labels).tolist())) < 2:
        return float('nan')
    return float(silhouette_score(np.asarray(D, dtype=np.float64), labels,
                                  metric='precomputed'))


def agreement(labels, y):
    """군집이 부담 구간을 재현하는 정도."""
    return {'ari': float(adjusted_rand_score(y, labels)),
            'nmi': float(normalized_mutual_info_score(y, labels))}


def high_burden_lift(labels, y):
    """군집별 고부담 비율과 전체 대비 리프트.

    ARI 가 0 근처여도 특정 군집에 고부담이 몰려 있으면 그것은 실재하는 신호다.
    """
    y = np.asarray(y)
    labels = np.asarray(labels)
    base = float(np.isin(y, HIGH_BURDEN).mean())
    out = {}
    for c in sorted(set(labels.tolist())):
        m = labels == c
        ratio = float(np.isin(y[m], HIGH_BURDEN).mean())
        out[int(c)] = {'n': int(m.sum()),
                       'high_ratio': ratio,
                       'lift': ratio / base if base else float('nan')}
    return out


def crosstab(labels, y):
    """군집 × 부담구간 교차표. {군집: {구간: 인원}}.

    ARI 는 5개 라벨이 통째로 일치하는가만 재므로 부분 신호를 지운다. 교차표를
    함께 봐야 '어느 군집에 고부담이 몰렸는가'가 보인다.
    """
    y = np.asarray(y)
    labels = np.asarray(labels)
    return {int(c): {lv: int(((labels == c) & (y == lv)).sum()) for lv in (1, 2, 3, 4, 5)}
            for c in sorted(set(labels.tolist()))}


def gate_contamination(labels, gate_rows):
    """군집이 설문 분기로 갈렸는지. 1 에 가까우면 '분기 군집'이다."""
    ids = [hash(tuple(r)) for r in gate_rows]
    if len(set(ids)) < 2:
        return 0.0
    return float(normalized_mutual_info_score(ids, labels))


def null_verdict(observed, null_scores, alpha=0.05):
    """실측 실루엣이 널 분포의 상위 alpha 밖인지 판정한다.

    이것이 없으면 '구조가 없다'와 '방법이 구조를 못 본다'를 구분할 수 없다.
    """
    null = np.asarray(null_scores, dtype=float)
    p = float((null >= observed).mean())
    return {'observed': float(observed),
            'null_mean': float(null.mean()),
            'null_max': float(null.max()),
            'p_value': p,
            'structured': bool(p < alpha)}
