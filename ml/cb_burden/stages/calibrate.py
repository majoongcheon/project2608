"""[3/4] 판정 불가 임계값 보정 (FR-009b·SC-016). ml/train.py stage_calibrate 이관.

임계값을 스펙에 고정하지 않고 학습 데이터로 도출한다(원칙 I). 조건은 둘이다.
  ① 판정 불가 비율이 10% 이하 ② 판정 불가군의 오분류율이 판정군보다 높다
"""
import numpy as np

from cb_burden import config
from cb_burden.stages import _core

MAX_UND = config.SUCCESS_CRITERIA['max_undecidable_rate']


def run(snap, base, sel, verbose=True):
    X, y, folds = _core.train_view(snap)
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in sel['selected']]
    Xs = X[:, cols]

    weights = sel['weights']
    r = _core.cv_scores(Xs, y, folds, sel['selected'], family=base['family'],
                        weights=weights)
    proba = r['oof_proba']
    pred = _core.decide(proba, weights)
    maxp = proba.max(axis=1)

    table = _core.build_freq_table(Xs, sel['selected'])
    rar = np.array([_core.rarity(Xs[i], sel['selected'], table) for i in range(len(Xs))])

    wrong = (pred != y)
    best = None
    for tc in np.quantile(maxp, np.arange(0.02, 0.31, 0.01)):
        for td in np.quantile(rar, np.arange(0.01, 0.16, 0.01)):
            und = (maxp < tc) | (rar < td)
            rate = und.mean()
            if rate <= 0 or rate > MAX_UND or (~und).sum() == 0:
                continue
            err_u, err_d = wrong[und].mean(), wrong[~und].mean()
            if err_u <= err_d:
                continue                # SC-016 전반부: 판정 불가 쪽이 더 틀려야 한다
            cand = {'tau_conf': float(tc), 'tau_dens': float(td), 'rate': float(rate),
                    'err_undecidable': float(err_u), 'err_decided': float(err_d)}
            if best is None or cand['rate'] < best['rate']:
                best = cand

    if best is None:
        best = {'tau_conf': float(np.quantile(maxp, 0.03)),
                'tau_dens': float(np.quantile(rar, 0.02)),
                'rate': None, 'err_undecidable': None, 'err_decided': None,
                'note': '조건을 만족하는 조합을 찾지 못해 보수적 분위값으로 대체'}
        if verbose:
            print('   ! SC-016 조건을 만족하는 조합 없음 — 보수적 기본값 사용')
    elif verbose:
        print(f"   τ_conf={best['tau_conf']:.4f} τ_dens={best['tau_dens']:.4f} · "
              f"판정불가 {best['rate']*100:.1f}% · 오분류율 "
              f"{best['err_undecidable']:.3f} > {best['err_decided']:.3f}")

    best['freq_table'] = table
    best['cv'] = {'macro_f1': r['macro_f1'], 'high_burden_recall': r['high_burden_recall']}
    return best
