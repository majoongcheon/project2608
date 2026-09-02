# -*- coding: utf-8 -*-
"""거리 행렬 위에서 군집화한다.

KMeans 를 쓰지 않는 이유 — 평균이 정의되지 않는다. 범주형이 섞인 데이터에서
"성별의 평균"은 뜻이 없다. 대신 실제 사람 하나를 중심으로 삼는 k-medoids(PAM)와
거리 행렬만으로 도는 계층군집을 쓴다.

sklearn_extra 가 설치돼 있지 않아 PAM 은 직접 구현한다(Park & Jun 의 교대 갱신).
"""
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


def pam(D, k, seed=0, max_iter=100):
    """k-medoids. 각 군집의 중심은 실제 데이터 점(medoid)이다."""
    D = np.asarray(D, dtype=np.float64)
    n = len(D)
    if k > n:
        raise ValueError(f'k={k} 가 표본 수 {n} 보다 크다')

    # 초기 medoid — 거리 합이 작은 점부터 고르면 시드에 덜 흔들린다(Park & Jun).
    order = np.argsort(D.sum(axis=1))
    medoids = list(order[:k])

    for _ in range(max_iter):
        labels = np.argmin(D[:, medoids], axis=1)

        moved = False
        for c in range(k):
            members = np.flatnonzero(labels == c)
            if len(members) == 0:
                # 빈 군집 — 현재 중심들에서 가장 먼 점을 새 medoid 로 준다
                far = int(np.argmax(np.min(D[:, medoids], axis=1)))
                if far != medoids[c]:
                    medoids[c] = far
                    moved = True
                continue
            within = D[np.ix_(members, members)].sum(axis=1)
            best = int(members[np.argmin(within)])
            if best != medoids[c]:
                medoids[c] = best
                moved = True
        if not moved:
            break

    return np.argmin(D[:, medoids], axis=1)


def hierarchical(D, k, method='average'):
    """계층군집. average linkage 는 거리 행렬만 있으면 되고 이상치에 둔감하다."""
    D = np.array(D, dtype=np.float64, copy=True)
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method=method)
    return fcluster(Z, t=k, criterion='maxclust') - 1
