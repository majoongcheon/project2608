"""라벨 품질 점검 — 부담 라벨(care_burden)이 믿을 만한가를 옆에서 조여 본다.

    PYTHONPATH=ml/.pylibs:ml python3 ml/HG_label_quality.py

무엇을 보는가
    ① 중복 응답     같은 답을 낸 사람끼리 라벨이 갈리는가 (7문항 시야 / 38변수 전체)
    ② 상관          라벨이 각 변수와 상식적인 방향으로 붙는가
    ③ 정보량 비교    변수를 7개 → 38개로 늘리면 성능이 오르는가
                    → 오르면 '문항 부족', 안 오르면 '설문과 라벨의 관계 자체가 약함'

안전
    - 스냅샷만 읽는다. DB 도 배포본도 건드리지 않는다.
    - test 602건을 쓰지 않는다. train 2,398건의 고정 5-fold 만 쓴다.
    - 아무 파일도 쓰지 않는다.
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'ml'))

import numpy as np                                                    # noqa: E402
from scipy.stats import spearmanr                                     # noqa: E402

from cb_burden.data import snapshot                                   # noqa: E402
from cb_burden.stages import _core                                    # noqa: E402

SNAP = ROOT / 'data' / 'snapshots' / 'cb_dataset_2026-09-01.csv.gz'


def duplicates(name, X, y, cols):
    """같은 응답 조합을 낸 사람끼리 라벨이 갈리는지 센다."""
    g = defaultdict(list)
    for row, lab in zip(X[:, cols], y):
        g[tuple(int(v) for v in row)].append(int(lab))
    multi = {k: v for k, v in g.items() if len(v) >= 2}
    conflict = {k: v for k, v in multi.items() if len(set(v)) > 1}
    # 고부담(1~2)이냐 아니냐에서도 갈리는지 — 서비스가 실제로 쓰는 구분이다
    binconf = {k: v for k, v in multi.items() if len({l <= 2 for l in v}) > 1}
    spread = Counter(max(v) - min(v) for v in conflict.values())
    # 천장 — 조합마다 최빈 라벨을 맞힌다고 가정했을 때의 정확도
    ceil5 = sum(Counter(v).most_common(1)[0][1] for v in g.values()) / len(y)
    ceilb = sum(max(sum(1 for l in v if l <= 2), sum(1 for l in v if l > 2))
                for v in g.values()) / len(y)
    n = max(len(multi), 1)
    print(f'\n== {name} (변수 {len(cols)}개) ==')
    print(f'  서로 다른 응답 조합 {len(g)}개 · 2명 이상인 조합 {len(multi)}개')
    print(f'  라벨이 갈린 조합 {len(conflict)}개 = {len(conflict) / n * 100:.1f}%')
    print(f'  고부담/아님 에서도 갈린 조합 {len(binconf)}개 = {len(binconf) / n * 100:.1f}%')
    print('  갈린 폭  ' + (' · '.join(f'{k}칸 {spread[k]}개' for k in sorted(spread)) or '없음'))
    print(f'  천장 정확도  5구간 {ceil5 * 100:.1f}%  ·  고부담 2분류 {ceilb * 100:.1f}%')


def correlations(X, y, feats, top=12):
    print('\n== 각 변수와 라벨의 스피어만 상관 (|r| 상위) ==')
    print('  ※ care_burden 은 1=최고부담 인 역방향 척도다. 부호를 읽을 때 주의한다.')
    rs = []
    for j, f in enumerate(feats):
        m = X[:, j] != _core.config.MISSING_SENTINEL
        if m.sum() < 100:
            continue
        r, p = spearmanr(X[m, j], y[m])
        if not np.isnan(r):
            rs.append((abs(r), r, p, f, int(m.sum())))
    rs.sort(reverse=True)
    for _, r, p, f, n in rs[:top]:
        print(f'  {f:<32} r={r:+.3f}  p={p:.1e}  n={n}')
    print(f'  |r|>=0.20 인 변수 {sum(1 for a, *_ in rs if a >= 0.20)}개 · '
          f'|r|>=0.10 {sum(1 for a, *_ in rs if a >= 0.10)}개 (전체 {len(rs)}개)')


def compare(X, y, folds, feats, weights, cases):
    """변수를 더 넣으면 성능이 오르는가. 결정 가중치는 배포본 값으로 고정한다."""
    print('\n== 정보량 비교 — 고정 5-fold · 가중치 배포본 값 고정 ==')
    for name, cols, family in cases:
        t0 = time.time()
        r = _core.cv_scores(X[:, cols], y, folds, [feats[c] for c in cols],
                            family=family, weights=weights)
        pred = _core.decide(r['oof_proba'], weights)
        print(f'  {name:<20} F1 {r["macro_f1"]:.4f} · 재현율 {r["high_burden_recall"]:.4f} · '
              f'정확도 {(pred == y).mean() * 100:5.1f}% · '
              f'고부담2분류 {((pred <= 2) == (y <= 2)).mean() * 100:5.1f}% · '
              f'두칸+ {(np.abs(pred - y) >= 2).mean() * 100:4.1f}%  ({time.time() - t0:.0f}초)')


def main():
    snap = snapshot.read(SNAP)
    model = json.loads((ROOT / 'models' / 'model_v1.json').read_text(encoding='utf-8'))
    feats = snap['features']
    idx = {f: i for i, f in enumerate(feats)}
    X, y, folds = _core.train_view(snap)
    q7 = [idx[f] for f in model['features']]
    all38 = list(range(len(feats)))
    W = model['decision_weights']

    print(f'train {len(y)}건 · 변수 {len(feats)}개 · test 미사용')
    duplicates('모델이 쓰는 7문항', X, y, q7)
    duplicates('전체 38변수', X, y, all38)

    print('\n== 라벨 분포 (train) ==')
    c = Counter(int(v) for v in y)
    for k in sorted(c):
        print(f'  {k}: {c[k]:>5}  {c[k] / len(y) * 100:5.1f}%')

    correlations(X, y, feats)
    compare(X, y, folds, feats, W, [
        ('7문항 (배포본)', q7, 'logit'),
        ('38변수 로지스틱', all38, 'logit'),
        ('38변수 랜덤포레스트', all38, 'rf'),
    ])


if __name__ == '__main__':
    main()
