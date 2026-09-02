"""정규화 튜닝 — penalty·C 를 바꿔가며 교차검증으로 비교한다.

    PYTHONPATH=ml/.pylibs:ml python3 ml/HG_tune_regularization.py

무엇을 보는가
    ① 성능이 오르는가 — macro F1 · 고부담 재현율
    ② **계수가 안정되는가** — L1 은 소수 표본이 만든 큰 계수를 0 으로 눌러준다.
       5번 문항의 한 선택지는 6명 응답으로 계수가 +1.345 였다(HG_모델-데이터-분석 참조).

안전
    - 스냅샷만 읽는다. DB 도 배포본도 건드리지 않는다.
    - test 602건을 쓰지 않는다. train 2,398건의 고정 5-fold 만 쓴다.
    - 아무 파일도 쓰지 않는다(결과는 화면에만). 저장하려면 --out 을 준다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
sys.path.insert(0, str(ROOT / 'ml'))

import numpy as np                                                    # noqa: E402
from sklearn.preprocessing import OneHotEncoder                       # noqa: E402

from cb_burden.data import snapshot                                   # noqa: E402
from cb_burden.stages import _core                                    # noqa: E402

SNAP = ROOT / 'data' / 'snapshots' / 'cb_dataset_2026-09-01.csv.gz'

# 훑을 조합. 기본값(l2·C=1.0)이 첫 줄이라 비교 기준이 된다.
GRID = (
    [{'penalty': 'l2', 'C': c} for c in (1.0, 100.0, 10.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01)]
    + [{'penalty': 'l1', 'C': c} for c in (1.0, 0.5, 0.2, 0.1, 0.05, 0.02)]
)


def coef_stats(X, y, params):
    """전체 train 으로 한 번 적합해 계수의 모양을 본다.

    0 이 된 열이 많을수록 소수 표본이 만든 계수가 눌렸다는 뜻이다.
    """
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    Xoh = enc.fit_transform(X)
    m = _core.make_logit(**params)
    m.fit(Xoh, y)
    coef = np.abs(m.coef_)
    return {'zero_pct': float((coef < 1e-8).mean() * 100),
            'max_abs': float(coef.max()),
            'mean_abs': float(coef.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None, help='결과를 JSON 으로 저장할 경로')
    a = ap.parse_args()

    snap = snapshot.read(SNAP)
    model = json.loads((ROOT / 'models' / 'model_v1.json').read_text(encoding='utf-8'))
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in model['features']]
    X, y, folds = _core.train_view(snap)
    Xs = X[:, cols]

    print(f'입력 {Xs.shape[0]}건 × 문항 {Xs.shape[1]}개 · 고정 5-fold')
    print(f'기준(배포본) penalty=l2 C=1.0\n')
    print(f"{'penalty':>9} {'C':>7} {'macroF1':>9} {'고부담재현':>10} "
          f"{'계수0비율':>9} {'|계수|최대':>10} {'초':>5}")
    print('  ' + '─' * 66)

    rows = []
    for params in GRID:
        t0 = time.time()
        try:
            r = _core.cv_scores(Xs, y, folds, model['features'],
                                family='logit', logit_params=params)
            w, tuned = _core.tune_decision_weights(r['oof_proba'], y)
            cs = coef_stats(Xs, y, params)
        except Exception as e:                      # saga 가 수렴 못 할 수 있다
            print(f"{params['penalty']:>9} {params['C']:>7.2f}  실패: {str(e)[:40]}")
            continue
        dt = time.time() - t0
        rows.append({**params, 'macro_f1': tuned['macro_f1'],
                     'high_burden_recall': tuned['high_burden_recall'],
                     'weights': w, **cs, 'sec': round(dt, 1)})
        print(f"{params['penalty']:>9} {params['C']:>7.2f} {tuned['macro_f1']:>9.4f} "
              f"{tuned['high_burden_recall']:>10.4f} {cs['zero_pct']:>8.1f}% "
              f"{cs['max_abs']:>10.3f} {dt:>5.1f}")

    base = rows[0]
    print('\n기준 대비')
    best_f1 = max(rows, key=lambda r: r['macro_f1'])
    best_rec = max(rows, key=lambda r: r['high_burden_recall'])
    print(f"  macro F1 최고   {best_f1['penalty']} C={best_f1['C']} "
          f"{best_f1['macro_f1']:.4f} ({best_f1['macro_f1'] - base['macro_f1']:+.4f})")
    print(f"  재현율 최고     {best_rec['penalty']} C={best_rec['C']} "
          f"{best_rec['high_burden_recall']:.4f} "
          f"({best_rec['high_burden_recall'] - base['high_burden_recall']:+.4f})")
    l1 = [r for r in rows if r['penalty'] == 'l1']
    if l1:
        most = max(l1, key=lambda r: r['zero_pct'])
        print(f"  계수를 가장 많이 누른 것  l1 C={most['C']} "
              f"→ {most['zero_pct']:.1f}% 가 0 · |계수|최대 {most['max_abs']:.3f} "
              f"(기준 {base['max_abs']:.3f})")

    if a.out:
        Path(a.out).write_text(json.dumps(
            {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
             'note': 'train 2,398건 · 고정 5-fold OOF. test 미사용.',
             'baseline': {'penalty': 'l2', 'C': 1.0},
             'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'\n저장 {a.out}')


if __name__ == '__main__':
    main()
