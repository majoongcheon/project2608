"""데이터 쪽에 남은 여지 점검 — 두 가지를 잰다.

    PYTHONPATH=ml/.pylibs:ml python3 ml/HG_data_headroom.py [--out <경로>]

① 학습곡선   train 을 잘라가며 학습해 곡선이 아직 오르는지 본다.
             → 오르면 '더 모으면 오른다', 평평하면 '더 모아도 소용없다'
③ 라벨 재정의 입력·폴드는 그대로 두고 정답 라벨만 5구간 / 3구간 / 2분류로 바꿔 학습한다.
             → 서비스가 실제로 쓰는 구분은 고부담이냐 아니냐뿐이다(3·4·5는 화면이 같다)

판정 기준 — **돌리기 전에 정했다**
    ① 마지막 구간(80%→100%)의 증가폭이 폴드 간 표준편차보다 작으면 '평평'
    ③ 재현율을 5구간의 값으로 맞춘 뒤 고부담 여부 정확도가 +2.0%p 이상이면 '값어치 있음'

공정한 비교를 위해
    - macro F1 은 구간 개수가 다르면 비교할 수 없다. 공통 잣대는 '고부담 여부' 둘뿐이다.
    - 결정 가중치가 유리하게 작용하지 않도록 **재현율을 같은 값에 맞춘 뒤** 정확도를 비교한다.

안전
    - 스냅샷만 읽는다. DB · models/ · 실행 중인 서비스를 건드리지 않는다.
    - test 602건을 쓰지 않는다. train 2,398건의 고정 5-fold 만 쓴다.
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

from cb_burden import config                                          # noqa: E402
from cb_burden.data import snapshot                                   # noqa: E402
from cb_burden.stages import _core                                    # noqa: E402

SNAP = ROOT / 'data' / 'snapshots' / 'cb_dataset_2026-09-01.csv.gz'
FRACTIONS = (0.2, 0.4, 0.6, 0.8, 1.0)
REPEATS = 3                      # 잘라내기의 운을 줄인다


def targets(y):
    """정답 라벨의 세 가지 정의. 입력은 건드리지 않는다."""
    return {
        '5구간 (지금)': (y.copy(), [1, 2, 3, 4, 5], lambda p: p <= 2),
        '3구간 1/2/그외': (np.where(y <= 2, y, 3), [1, 2, 3], lambda p: p <= 2),
        '2분류 고부담/아님': (np.where(y <= 2, 1, 2), [1, 2], lambda p: p == 1),
    }


def fit_predict(Xtr, ytr, Xva, classes, boost):
    """고부담 쪽 구간에 boost 를 곱해 최종 구간을 고른다(배포본과 같은 방식)."""
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    A, B = enc.fit_transform(Xtr), enc.transform(Xva)
    m = _core.make_logit()
    m.fit(A, ytr)
    proba = m.predict_proba(B)
    # 학습 폴드에 없던 구간은 확률 0 으로 채워 자리를 맞춘다
    full = np.zeros((len(B), len(classes)))
    for i, c in enumerate(m.classes_):
        full[:, classes.index(int(c))] = proba[:, i]
    w = np.array([boost if c <= 2 else 1.0 for c in classes])
    if classes == [1, 2]:                     # 2분류는 1 이 고부담이다
        w = np.array([boost, 1.0])
    return np.asarray(classes)[(full * w).argmax(axis=1)]


def cv(X, yv, classes, is_high, folds, boost, frac=1.0, seed=0):
    """고정 5-fold. frac<1 이면 학습 폴드에서 층화 추출한다(평가 폴드는 온전히 둔다)."""
    rng = np.random.default_rng(config.SEED + seed)
    pred = np.zeros(len(yv), dtype=int)
    for k in sorted(set(folds)):
        tr, va = np.where(folds != k)[0], folds == k
        if frac < 1.0:
            keep = []
            for c in np.unique(yv[tr]):                      # 층화 — 구간 비율을 지킨다
                pool = tr[yv[tr] == c]
                keep.append(rng.choice(pool, max(1, int(round(len(pool) * frac))),
                                       replace=False))
            tr = np.concatenate(keep)
        pred[va] = fit_predict(X[tr], yv[tr], X[va], classes, boost)
    return pred


def scores(pred, yv, y5, is_high):
    """공통 잣대 — 고부담 여부 하나로만 잰다."""
    ph, ah = is_high(pred), (y5 <= 2)
    return {'recall': float((ph & ah).sum() / ah.sum()),
            'acc_high': float((ph == ah).mean())}


def at_matched_recall(X, yv, classes, is_high, folds, y5, target_recall):
    """재현율을 target 이상으로 맞춘 운전점 중 정확도가 가장 높은 것을 고른다."""
    best = None
    for boost in np.arange(1.0, 3.01, 0.05):
        s = scores(cv(X, yv, classes, is_high, folds, boost), yv, y5, is_high)
        if s['recall'] >= target_recall and (best is None or s['acc_high'] > best[1]['acc_high']):
            best = (round(float(boost), 2), s)
    if best is None:                       # 맞출 수 없으면 재현율이 가장 높은 운전점
        cands = [(round(float(b), 2), scores(cv(X, yv, classes, is_high, folds, b), yv, y5, is_high))
                 for b in np.arange(1.0, 4.01, 0.1)]
        best = max(cands, key=lambda t: t[1]['recall'])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    snap = snapshot.read(SNAP)
    model = json.loads((ROOT / 'models' / 'model_v1.json').read_text(encoding='utf-8'))
    idx = {f: i for i, f in enumerate(snap['features'])}
    X, y, folds = _core.train_view(snap)
    X = X[:, [idx[f] for f in model['features']]]
    W = model['decision_weights']
    boost0 = float(W[0])
    out = {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'note': 'train 2,398건 · 고정 5-fold · test 미사용. DB·models/ 미접근.'}

    print(f'train {len(y)}건 · 문항 {X.shape[1]}개 · 고정 5-fold · 고부담 가중치 {boost0}\n')

    # ── ① 학습곡선 ──────────────────────────────────────────────
    print('=== ① 학습곡선 — 데이터를 더 모으면 오르는가 ===')
    print(f"  {'학습에 쓴 양':>14} {'고부담 재현율':>14} {'고부담 여부 정확도':>18} {'폴드간 표준편차':>16}")
    curve = []
    for f in FRACTIONS:
        accs, recs = [], []
        for s in range(REPEATS):
            pred = cv(X, y, [1, 2, 3, 4, 5], lambda p: p <= 2, folds, boost0, frac=f, seed=s)
            per = [scores(pred[folds == k], y[folds == k], y[folds == k], lambda p: p <= 2)
                   for k in sorted(set(folds))]
            accs.append(np.mean([p['acc_high'] for p in per]))
            recs.append(np.mean([p['recall'] for p in per]))
            if s == 0:
                fold_sd = float(np.std([p['acc_high'] for p in per], ddof=1))
        n = int(round(len(y) * (len(set(folds)) - 1) / len(set(folds)) * f))
        row = {'frac': f, 'n_per_fold': n, 'recall': float(np.mean(recs)),
               'acc_high': float(np.mean(accs)), 'fold_sd': fold_sd}
        curve.append(row)
        print(f"  {f * 100:>10.0f}% ({n:>4}건) {row['recall']:>13.4f} "
              f"{row['acc_high'] * 100:>16.1f}% {fold_sd * 100:>14.1f}%p")
    gain = (curve[-1]['acc_high'] - curve[-2]['acc_high']) * 100
    sd = curve[-1]['fold_sd'] * 100
    flat = abs(gain) < sd
    print(f"\n  마지막 구간(80%→100%) 증가폭 {gain:+.1f}%p · 폴드간 표준편차 {sd:.1f}%p")
    print(f"  → {'평평하다. 더 모아도 크게 달라지지 않는다.' if flat else '아직 오르는 중이다. 더 모으면 오른다.'}")
    out['learning_curve'] = {'rows': curve, 'last_gain_pp': gain, 'fold_sd_pp': sd, 'flat': bool(flat)}

    # ── ③ 라벨 재정의 ────────────────────────────────────────────
    print('\n=== ③ 라벨 재정의 — 5구간을 고집할 이유가 있는가 ===')
    base_pred = cv(X, y, [1, 2, 3, 4, 5], lambda p: p <= 2, folds, boost0)
    base = scores(base_pred, y, y, lambda p: p <= 2)
    print(f"  기준선(5구간 · 가중치 {boost0}) 재현율 {base['recall']:.4f} · "
          f"정확도 {base['acc_high'] * 100:.1f}%")
    print(f"  아래는 모두 **재현율을 {base['recall']:.4f} 이상으로 맞춘 뒤** 정확도를 비교한 값이다.\n")
    print(f"  {'라벨 정의':<20} {'가중치':>7} {'고부담 재현율':>14} {'고부담 여부 정확도':>18} {'기준 대비':>12}")
    rows = []
    for name, (yv, classes, is_high) in targets(y).items():
        boost, s = at_matched_recall(X, yv, classes, is_high, folds, y, base['recall'])
        d = (s['acc_high'] - base['acc_high']) * 100
        rows.append({'name': name, 'boost': boost, **s, 'delta_pp': d})
        print(f"  {name:<20} {boost:>7.2f} {s['recall']:>14.4f} "
              f"{s['acc_high'] * 100:>17.1f}% {d:>+11.1f}%p")
    best = max(rows[1:], key=lambda r: r['acc_high'])
    worth = best['delta_pp'] >= 2.0
    print(f"\n  천장(같은 답=같은 라벨 가정) 85.0%")
    print(f"  가장 나은 대안 {best['name']} {best['delta_pp']:+.1f}%p")
    print(f"  → {'재정의가 값어치 있다. 팀에 올린다.' if worth else '기준(+2.0%p)에 못 미친다. 5구간을 유지한다.'}")
    out['relabel'] = {'baseline': base, 'rows': rows, 'worth': bool(worth), 'threshold_pp': 2.0}

    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'\n저장 {a.out}')


if __name__ == '__main__':
    main()
