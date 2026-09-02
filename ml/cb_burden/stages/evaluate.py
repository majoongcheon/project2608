"""[평가] test 602건 — 단 한 번만 실행 (SC-004·SC-005·SC-016).

ml/train.py stage_evaluate 이관. **DB 를 건드리지 않는다** — 기록은 cb_burden.data.record
가 맡는다. 그렇게 나눠야 평가를 다시 돌려도 남의 기록을 덮지 않는다(2026-09-01 사고).
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

from cb_burden import config
from cb_burden.explain.saabas import predict_proba
from cb_burden.stages import _core

SC = config.SUCCESS_CRITERIA


def _baseline_on_test(snap, payload):
    """설명변수 전체 모델을 train 으로 학습해 test 에서 평가한다 (동일 조건 비교).

    CV 값과 test 값을 섞어 비교하면 추정 방식이 달라 SC-004·SC-005 의 '대비 손실'이
    왜곡된다. 그래서 기준 모델도 같은 test 에서 잰다.
    """
    X, y, _ = _core.train_view(snap)
    Xt, yt = _core.test_view(snap)
    w = payload.get('decision_weights')
    if payload['family'] == 'logit':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        m = LogisticRegression(max_iter=2000, random_state=config.SEED)
        m.fit(enc.fit_transform(X), y)
        proba = m.predict_proba(enc.transform(Xt))
    else:
        m = _core.make_model(payload['family'])
        m.fit(X, y)
        proba = m.predict_proba(Xt)
    pred = _core.decide(proba, w)
    return _core.macro_f1(yt, pred), _core.high_burden_recall(yt, pred)


def run(snap, payload, unc, verbose=True):
    feats = payload['features']
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in feats]
    Xt_all, yt = _core.test_view(snap)
    Xt = Xt_all[:, cols]

    table, tc, td = unc['freq_table'], unc['tau_conf'], unc['tau_dens']
    proba = np.array([predict_proba(payload, list(row)) for row in Xt])
    pred = _core.decide(proba, payload.get('decision_weights'))
    maxp = proba.max(axis=1)
    rar = np.array([_core.rarity(Xt[i], feats, table) for i in range(len(Xt))])
    und = (maxp < tc) | (rar < td)

    f1 = _core.macro_f1(yt, pred)
    rec = _core.high_burden_recall(yt, pred)
    bf1, brec = _baseline_on_test(snap, payload)

    verdict = {
        'SC-004 macro F1 손실 <= 0.03': bool(bf1 - f1 <= SC['max_f1_loss']),
        'SC-005 재현율 손실 <= 0.05': bool(brec - rec <= SC['max_recall_loss']),
        'SC-005 재현율 >= 0.70': bool(rec >= SC['min_recall_abs']),
        'SC-016 판정불가 <= 10%': bool(und.mean() <= SC['max_undecidable_rate']),
    }

    if verbose:
        print(f"   macro F1          {f1:.4f}  (기준 모델 {bf1:.4f}, 손실 {bf1 - f1:+.4f})")
        print(f"   고부담 재현율      {rec:.4f}  (기준 모델 {brec:.4f}, 손실 {brec - rec:+.4f})")
        print(f"   판정 불가 비율     {und.mean() * 100:.1f}%")
        if und.sum() and (~und).sum():
            print(f"   오분류율          판정불가 {(pred[und] != yt[und]).mean():.3f} "
                  f"vs 판정 {(pred[~und] != yt[~und]).mean():.3f}")
        for k, v in verdict.items():
            print(f"   {'PASS' if v else 'FAIL'}  {k}")

    return {'macro_f1': f1, 'high_burden_recall': rec,
            'undecidable_rate': float(und.mean()),
            'baseline': {'macro_f1': bf1, 'high_burden_recall': brec},
            'verdict': verdict}
