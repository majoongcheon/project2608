"""[2/4] 문항 선별 — 후진 제거 (FR-004c). ml/train.py stage_select 이관.

k_target 은 환경변수가 아니라 인자로 받는다. 0 이면 규칙(최소 k)을 따른다.
"""
import numpy as np

from cb_burden import config
from cb_burden.stages import _core

SC = config.SUCCESS_CRITERIA


def run(snap, base, k_target=0, min_k=3, verbose=True):
    X, y, folds = _core.train_view(snap)
    fam = base['family']
    all_feats = list(snap['features'])
    cur = list(all_feats)
    idx = {f: i for i, f in enumerate(all_feats)}
    history, dropped = [], []

    while len(cur) > min_k:
        cols = [idx[f] for f in cur]
        r = _core.cv_scores(X[:, cols], y, folds, cur, family=fam, want_importance=True)
        w, tuned = _core.tune_decision_weights(r['oof_proba'], y)
        f1_loss = base['B_f1'] - tuned['macro_f1']
        rec_loss = base['B_rec'] - tuned['high_burden_recall']
        okay = (f1_loss <= SC['max_f1_loss'] - config.F1_MARGIN
                and rec_loss <= SC['max_recall_loss']
                and tuned['high_burden_recall'] >= SC['min_recall_abs'] + config.REC_MARGIN)
        history.append({'k': len(cur), 'macro_f1': tuned['macro_f1'],
                        'high_burden_recall': tuned['high_burden_recall'],
                        'decision_weights': w, 'f1_loss': f1_loss,
                        'rec_loss': rec_loss, 'passes': okay})
        if verbose:
            print(f"   k={len(cur):2d}  F1 {tuned['macro_f1']:.4f} (손실 {f1_loss:+.4f}) · "
                  f"재현율 {tuned['high_burden_recall']:.4f} (손실 {rec_loss:+.4f})  "
                  f"{'OK' if okay else '미달'}")
        if not okay:
            break
        imp = r.get('importance')
        if imp is None:
            break
        worst = cur[int(np.argmin(imp))]
        dropped.append(worst)
        cur = [f for f in cur if f != worst]

    passing = [h for h in history if h['passes']]
    rule_k = min(h['k'] for h in passing) if passing else len(all_feats)
    if k_target:
        found = [h for h in history if h['k'] == k_target]
        if not found:
            raise ValueError(
                f'k_target={k_target} 가 탐색 경로에 없습니다: {[h["k"] for h in history]}')
        if not found[0]['passes']:
            raise ValueError(f'k_target={k_target} 는 SC-004·SC-005 정지 조건을 만족하지 않습니다')
        best_k, k_source = k_target, 'k_target (제품 판단)'
    else:
        best_k, k_source = rule_k, '규칙 (최소 k)'

    chosen = next((h for h in history if h['k'] == best_k), history[0])
    n_drop = len(all_feats) - best_k
    selected = [f for f in all_feats if f not in dropped[:n_drop]]
    if verbose:
        print(f"   → 최소 문항 집합 k={len(selected)} (탈락 {n_drop}개)")
    return {'selected': selected, 'dropped_order': dropped, 'history': history,
            'weights': chosen['decision_weights'],
            'k_source': k_source, 'rule_k': rule_k,
            'stop_rule': {'max_f1_loss': SC['max_f1_loss'],
                          'max_rec_loss': SC['max_recall_loss'],
                          'min_rec_abs': SC['min_recall_abs']},
            'baseline': {'macro_f1': base['B_f1'],
                         'high_burden_recall': base['B_rec'],
                         'n_features': len(all_feats)}}
