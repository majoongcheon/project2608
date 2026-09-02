"""서열 모델 실험 — 다섯 중 하나 고르기를 네 번의 예/아니오로 바꾼다.

    PYTHONPATH=ml/.pylibs:ml python3 ml/HG_ordinal.py [--out <경로>]

계획서 `docs/HG_서열모델-계획.md` 를 따른다. 판단 기준은 **실행 전에 정해져 있다**(5.1).

안전
    - 스냅샷만 읽는다. DB 도 배포본도 건드리지 않는다.
    - test 602건을 쓰지 않는다. train 2,398건의 고정 5-fold 만 쓴다.
    - --out 을 주지 않으면 아무 파일도 쓰지 않는다.
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
CUTS = (1, 2, 3, 4)          # P(y<=1) … P(y<=4)
LAB = {1: '최고부담', 2: '고부담', 3: '중간', 4: '저부담', 5: '없음'}


def ordinal_proba(Xtr, ytr, Xva, logit_params=None):
    """네 개의 예/아니오 모델을 학습해 5구간 확률로 되돌린다.

    반환 (확률 5열, 단조성을 어긴 행 수).
    """
    cum = np.zeros((len(Xva), len(CUTS)))
    for i, t in enumerate(CUTS):
        m = _core.make_logit(**(logit_params or {}))
        m.fit(Xtr, (ytr <= t).astype(int))
        # classes_ 가 [0,1] 이므로 1(=예) 쪽 확률을 쓴다.
        # 한쪽 답만 있는 폴드면 클래스가 하나뿐이라 그 값으로 채운다.
        if len(m.classes_) == 1:
            cum[:, i] = float(m.classes_[0])
        else:
            cum[:, i] = m.predict_proba(Xva)[:, list(m.classes_).index(1)]

    # 단조성 — P(y<=1) <= P(y<=2) <= … 이어야 한다. 어긴 행을 센 뒤 강제한다.
    violated = int((np.diff(cum, axis=1) < -1e-12).any(axis=1).sum())
    cum = np.maximum.accumulate(cum, axis=1)

    p = np.zeros((len(Xva), 5))
    p[:, 0] = cum[:, 0]
    for i in range(1, len(CUTS)):
        p[:, i] = cum[:, i] - cum[:, i - 1]
    p[:, 4] = 1.0 - cum[:, -1]
    p = np.clip(p, 0.0, None)
    s = p.sum(axis=1, keepdims=True)
    return p / np.where(s == 0, 1.0, s), violated


def run_cv(Xs, y, folds, weights, mode, logit_params=None):
    """폴드마다 학습·평가하고 폴드별 지표를 돌려준다."""
    out = {'macro_f1': [], 'recall': [], 'far2': [], 'violated': 0, 'n': 0,
           'pred': np.zeros(len(y), dtype=int), 'maxp': np.zeros(len(y))}
    for k in sorted(set(folds)):
        tr, va = folds != k, folds == k
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        Xtr, Xva = enc.fit_transform(Xs[tr]), enc.transform(Xs[va])

        if mode == 'ordinal':
            proba, v = ordinal_proba(Xtr, y[tr], Xva, logit_params)
            out['violated'] += v
        else:
            m = _core.make_logit(**(logit_params or {}))
            m.fit(Xtr, y[tr])
            proba = m.predict_proba(Xva)
        out['n'] += int(va.sum())

        pred = _core.decide(proba, weights)
        out['pred'][va] = pred
        out['maxp'][va] = proba.max(axis=1)
        out['macro_f1'].append(_core.macro_f1(y[va], pred))
        out['recall'].append(_core.high_burden_recall(y[va], pred))
        out['far2'].append(float((np.abs(pred - y[va]) >= 2).mean()))
    for k in ('macro_f1', 'recall', 'far2'):
        out[k] = np.array(out[k])
    return out


def show(tag, r):
    print(f"  {tag:<10} " + ' '.join(f'{v:.4f}' for v in r['macro_f1'])
          + f"  평균 {r['macro_f1'].mean():.4f} ±{r['macro_f1'].std(ddof=1):.4f}")


def paired(a, b, name, lower_better=False):
    """같은 폴드끼리 뺀다. 폴드 자체의 난이도가 상쇄된다.

    lower_better 는 '두 칸 이상 오류'처럼 작을수록 좋은 지표를 위한 것이다.
    이 경우 서열이 이긴 폴드는 차이가 **음수**인 폴드다.
    """
    d = b - a
    se = d.std(ddof=1) / np.sqrt(len(d))
    win = int((d < 0).sum() if lower_better else (d > 0).sum())
    print(f"  {name:<22} " + ' '.join(f'{v:+.4f}' for v in d)
          + f"  평균 {d.mean():+.4f} · 서열이 이긴 폴드 {win}/{len(d)}"
          + (f" · t={d.mean() / se:.2f}" if se > 0 else ""))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    snap = snapshot.read(SNAP)
    model = json.loads((ROOT / 'models' / 'model_v1.json').read_text(encoding='utf-8'))
    idx = {f: i for i, f in enumerate(snap['features'])}
    cols = [idx[f] for f in model['features']]
    X, y, folds = _core.train_view(snap)
    Xs = X[:, cols]
    W = model['decision_weights']          # 배포본 값으로 고정 — 공정 비교

    print(f'입력 {Xs.shape[0]}건 · 문항 {Xs.shape[1]}개 · 고정 5-fold')
    print(f'결정 가중치 {W} (배포본 값으로 고정)\n')

    t0 = time.time()
    base = run_cv(Xs, y, folds, W, mode='multi')
    ordi = run_cv(Xs, y, folds, W, mode='ordinal')
    print(f'학습 완료 ({time.time() - t0:.1f}초)\n')

    print('=== 폴드별 macro F1 ===')
    print(f"  {'':<10} " + ' '.join(f'폴드{k}' for k in sorted(set(folds))))
    show('지금(다항)', base)
    show('서열', ordi)

    print('\n=== 폴드별 고부담 재현율 ===')
    for tag, r in (('지금(다항)', base), ('서열', ordi)):
        print(f"  {tag:<10} " + ' '.join(f'{v:.4f}' for v in r['recall'])
              + f"  평균 {r['recall'].mean():.4f}")

    print('\n=== 폴드별 두 칸 이상 오류 비율 ===')
    for tag, r in (('지금(다항)', base), ('서열', ordi)):
        print(f"  {tag:<10} " + ' '.join(f'{v:.4f}' for v in r['far2'])
              + f"  평균 {r['far2'].mean() * 100:.1f}%")

    print('\n=== 짝지어 비교 (서열 − 지금) ===')
    paired(base['macro_f1'], ordi['macro_f1'], 'macro F1')
    paired(base['recall'], ordi['recall'], '고부담 재현율')
    paired(base['far2'], ordi['far2'], '두칸이상(낮을수록 좋음)', lower_better=True)

    print('\n=== 오류 구성 ===')
    for tag, r in (('지금(다항)', base), ('서열', ordi)):
        d = np.abs(r['pred'] - y)
        print(f"  {tag:<10} " + ' · '.join(
            f'{k}칸 {int((d == k).sum()) / len(y) * 100:4.1f}%' for k in range(5)))

    print('\n=== 서열 모델의 단조성 ===')
    vr = ordi['violated'] / ordi['n'] * 100
    print(f"  위반 {ordi['violated']}건 / {ordi['n']}건 = {vr:.2f}%")

    print('\n=== 판정 불가에 미칠 영향 (참고) ===')
    unc = json.loads((ROOT / 'models' / 'uncertainty_v1.json').read_text(encoding='utf-8'))
    for tag, r in (('지금(다항)', base), ('서열', ordi)):
        below = float((r['maxp'] < unc['tau_conf']).mean() * 100)
        print(f"  {tag:<10} 최대확률 중앙값 {np.median(r['maxp']):.4f} · "
              f"지금 문턱({unc['tau_conf']:.4f}) 아래 {below:.2f}%")

    print('\n=== 계획서 5.1 기준으로 판정 ===')
    checks = [
        ('고부담 재현율 유지', ordi['recall'].mean() >= base['recall'].mean(),
         f"{ordi['recall'].mean():.4f} vs {base['recall'].mean():.4f}"),
        ('두 칸 이상 오류 감소', ordi['far2'].mean() <= base['far2'].mean(),
         f"{ordi['far2'].mean() * 100:.1f}% vs {base['far2'].mean() * 100:.1f}%"),
        ('macro F1 유지', ordi['macro_f1'].mean() >= base['macro_f1'].mean(),
         f"{ordi['macro_f1'].mean():.4f} vs {base['macro_f1'].mean():.4f}"),
        ('단조성 위반 5% 미만', vr < 5.0, f'{vr:.2f}%'),
    ]
    for name, ok, detail in checks:
        print(f"  {'통과' if ok else '미달'}  {name:<22} {detail}")
    print(f"\n  → {'다음 단계 검토 대상' if all(c[1] for c in checks) else '기각'}")

    if a.out:
        Path(a.out).write_text(json.dumps({
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'note': 'train 2,398건 · 고정 5-fold. test 미사용. 결정 가중치는 배포본 값 고정.',
            'decision_weights': W,
            'baseline': {k: base[k].tolist() for k in ('macro_f1', 'recall', 'far2')},
            'ordinal': {k: ordi[k].tolist() for k in ('macro_f1', 'recall', 'far2')},
            'monotonicity_violation_pct': vr,
            'checks': [{'name': n, 'pass': bool(o), 'detail': d} for n, o, d in checks],
        }, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'\n저장 {a.out}')


if __name__ == '__main__':
    main()
