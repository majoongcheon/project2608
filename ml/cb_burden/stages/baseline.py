"""[1/4] 기준 모델 — 설명변수 전체로 계열을 비교한다. ml/train.py stage_baseline 이관."""
import time

from cb_burden import config
from cb_burden.stages import _core

MIN_REC_ABS = config.SUCCESS_CRITERIA['min_recall_abs']


def run(snap, families=('rf', 'et', 'logit'), verbose=True):
    X, y, folds = _core.train_view(snap)
    feats = snap['features']
    results = {}
    for fam in families:
        t0 = time.time()
        raw = _core.cv_scores(X, y, folds, feats, family=fam)
        w, tuned = _core.tune_decision_weights(raw['oof_proba'], y)
        results[fam] = {
            'macro_f1': tuned['macro_f1'],
            'high_burden_recall': tuned['high_burden_recall'],
            'decision_weights': w,
            'argmax_only': {'macro_f1': raw['macro_f1'],
                            'high_burden_recall': raw['high_burden_recall']},
        }
        if verbose:
            print(f"   {fam:6s} macro F1 {tuned['macro_f1']:.4f} · 고부담 재현율 "
                  f"{tuned['high_burden_recall']:.4f} · 가중치 {w[0]:.2f}  "
                  f"({time.time() - t0:.1f}s)")

    # 재현율 하한을 만족하는 계열 중 macro F1 이 가장 높은 것. 하나도 없으면 재현율 우선.
    ok = [f for f, r in results.items()
          if r['high_burden_recall'] >= MIN_REC_ABS + config.REC_MARGIN]
    best = max(ok or list(results), key=lambda f: results[f]['macro_f1'])
    if verbose:
        print(f"   → 채택 계열: {best} · 결정 가중치 {results[best]['decision_weights']}")
    return {'family': best, 'results': results,
            'weights': results[best]['decision_weights'],
            'B_f1': results[best]['macro_f1'],
            'B_rec': results[best]['high_burden_recall']}
