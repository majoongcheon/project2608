# -*- coding: utf-8 -*-
"""CHJ-02 · 척도를 살린 인코딩이 실제로 도움이 되는가 (최호준).

`cb_feature_meta_v1.var_scale` 은 38변수 전부가 순서형인지 명목형인지 기록하고 있는데
파이프라인이 한 번도 참조하지 않는다. 배포본 로지스틱은 7문항을 **전부 one-hot** 으로
넣는다 — 순서형 4개("1 전혀 지지 안함 ~ 5 매우 지지")의 순서를 통째로 버린다.

인코딩만 바꿔 여섯 가지를 비교한다. 모델·문항·평가 절차는 전부 고정한다.
효과를 분리해서 봐야 무엇이 기여했는지 알 수 있으므로 단독안과 결합안을 함께 둔다.

  onehot           현재 배포본 방식 (7문항 전부 one-hot)
  scale            순서형을 직선 하나로 + 결측 지시자, 명목형만 one-hot
  thermo           순서형을 누적 더미로 (순서는 살리되 직선을 강요하지 않는다)
  collapse         one-hot 은 그대로 두고 희소 수준만 병합       ← 병합 효과만 분리
  scale_collapse   scale + collapse
  thermo_collapse  thermo + collapse

★ test 602건은 사용하지 않는다. train 2,398건만 쓴다.

비교 절차는 CHJ-01(앙상블 실험)과 동일하다 — 클래스 배수를 fold 학습 부분의 내부 CV
에서만 고르고, 반복 CV(분할 잡음)와 행 부트스트랩(표본 잡음) 두 구간을 함께 낸다.

  python3 ml/CHJ-encoding-compare.py
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in ('ml/.pylibs-sjh', 'ml/.pylibs', 'ml'):
    sys.path.insert(0, str(ROOT / p))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import StratifiedKFold

import db as dbmod

# CHJ-01 의 측정 장치를 그대로 쓴다. 파일명에 하이픈이 있어 importlib 로 불러온다.
# 검증된 코드를 복사하지 않기 위함이다 — 지표는 sklearn 과 1e-12 이내 일치가 확인돼 있다.
_spec = importlib.util.spec_from_file_location('chj01', ROOT / 'ml' / 'CHJ-ensemble-compare.py')
chj01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chj01)

CLASSES = chj01.CLASSES
METRIC_KEYS = chj01.METRIC_KEYS
HIGH_BURDEN = chj01.HIGH_BURDEN
metrics, decide, align = chj01.metrics, chj01.decide, chj01.align
tune_class_weights = chj01.tune_class_weights
t_interval, bootstrap_diffs, verdict = chj01.t_interval, chj01.bootstrap_diffs, chj01.verdict

SEED = 20260902
MISSING = -1
RARE_MIN = 30          # 학습 부분에서 이보다 적은 수준은 '기타'로 묶는다
BASELINE = 'onehot'

LABELS = {
    'onehot': 'onehot (현재 배포본 방식)',
    'scale': 'scale (순서형을 직선 하나로)',
    'thermo': 'thermo (순서형을 누적 더미로)',
    'collapse': 'collapse (희소 수준 병합만)',
    'scale_collapse': 'scale+collapse',
    'thermo_collapse': 'thermo+collapse',
}


# ─────────────────────────────────────────────────────── 인코더
def collapse_column(col_tr, col_va, scale):
    """학습 부분에서만 희소 수준을 찾아 병합한다. 검증 부분은 그 규칙을 따르기만 한다."""
    obs = col_tr[col_tr != MISSING]
    vals, cnt = np.unique(obs, return_counts=True)
    rare = set(vals[cnt < RARE_MIN].tolist())
    if not rare:
        return col_tr.copy(), col_va.copy()

    if scale == 'ordinal':
        # 순서형은 순서를 깨지 않도록 이웃 수준으로 흡수한다(양 끝의 희소 수준을 안으로 당김).
        keep = sorted(set(vals.tolist()) - rare)
        if not keep:
            return col_tr.copy(), col_va.copy()
        lo, hi = keep[0], keep[-1]

        def clip(c):
            out = c.copy()
            m = out != MISSING
            out[m] = np.clip(out[m], lo, hi)
            return out
        return clip(col_tr), clip(col_va)

    # 명목형은 희소 수준을 하나의 '기타' 코드로 모은다.
    other = float(max(vals.max(), col_va.max()) + 1)

    def merge(c):
        out = c.copy()
        out[np.isin(out, list(rare))] = other
        return out
    return merge(col_tr), merge(col_va)


def thermometer(col_tr, col_va):
    """누적 더미 — 값 v 를 [v>=L2, v>=L3, ...] 로 편다.

    one-hot 과 열 수는 거의 같지만 뜻이 다르다. one-hot 의 계수는 '수준별 효과'라
    L2 벌점이 수준을 각자 0으로 당긴다. 누적 더미의 계수는 '한 칸 올라갈 때의 증분'이라
    벌점이 증분을 당긴다 — 즉 순서를 존중하면서도 직선을 강요하지 않는다.
    """
    levels = sorted(set(col_tr[col_tr != MISSING].tolist()))

    def build(c):
        v = c.astype(float)
        miss = (v == MISSING).astype(float)
        cols = [(v >= L).astype(float) * (1 - miss) for L in levels[1:]]
        cols.append(miss)
        return np.column_stack(cols) if cols else np.zeros((len(v), 1))
    return build(col_tr), build(col_va)


def encode(kind, Xtr, Xva, scales):
    """설계행렬을 만든다. one-hot 은 반드시 학습 부분에서만 fit 한다."""
    use_scale = kind in ('scale', 'scale_collapse')
    use_thermo = kind in ('thermo', 'thermo_collapse')
    use_collapse = kind in ('collapse', 'scale_collapse', 'thermo_collapse')

    cols_tr, cols_va = [], []
    onehot_idx, binary_idx = [], []
    for j, sc in enumerate(scales):
        a, b = Xtr[:, j], Xva[:, j]
        if use_collapse:
            a, b = collapse_column(a, b, sc)

        if use_thermo and sc == 'ordinal':
            ta, tb = thermometer(a, b)
            binary_idx.append(len(cols_tr))       # 이미 0/1 이라 표준화하지 않는다
            cols_tr.append(ta); cols_va.append(tb)
        elif use_scale and sc == 'ordinal':
            # 순서형 — 값을 그대로 쓰되 결측은 학습 중앙값으로 채우고 지시자를 따로 둔다.
            obs = a[a != MISSING]
            fill = float(np.median(obs)) if len(obs) else 0.0
            for c, dst in ((a, cols_tr), (b, cols_va)):
                v = c.astype(float).copy()
                miss = (v == MISSING).astype(float)
                v[v == MISSING] = fill
                dst.append(np.column_stack([v, miss]))
        else:
            onehot_idx.append(len(cols_tr))
            cols_tr.append(a.reshape(-1, 1))
            cols_va.append(b.reshape(-1, 1))

    # one-hot 대상 열만 모아 한 번에 변환한다.
    Atr_parts, Ava_parts = [], []
    if onehot_idx:
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        raw_tr = np.hstack([cols_tr[i] for i in onehot_idx])
        raw_va = np.hstack([cols_va[i] for i in onehot_idx])
        Atr_parts.append(enc.fit_transform(raw_tr))
        Ava_parts.append(enc.transform(raw_va))
    for i in binary_idx:                      # 누적 더미 — 0/1 그대로 둔다
        Atr_parts.append(cols_tr[i]); Ava_parts.append(cols_va[i])
    num_idx = [i for i in range(len(cols_tr)) if i not in onehot_idx and i not in binary_idx]
    if num_idx:
        Ntr = np.hstack([cols_tr[i] for i in num_idx])
        Nva = np.hstack([cols_va[i] for i in num_idx])
        # L2 벌점이 열마다 공평하게 걸리도록 표준화한다. 모델의 표현력을 바꾸지는 않는다.
        mu, sd = Ntr.mean(axis=0), Ntr.std(axis=0)
        sd[sd == 0] = 1.0
        Atr_parts.append((Ntr - mu) / sd)
        Ava_parts.append((Nva - mu) / sd)
    return np.hstack(Atr_parts), np.hstack(Ava_parts)


def fit_logit(Atr, ytr, Ava):
    m = LogisticRegression(max_iter=2000, random_state=SEED)
    m.fit(Atr, ytr)
    return align(m.predict_proba(Ava), m.classes_)


# ───────────────────────────────────────────── 반복 1회 = 바깥 5-fold
def run_repeat(X, y, folds, scales, kinds, inner_splits, width_log):
    pred = {k: np.zeros(len(y), dtype=int) for k in kinds}
    for f in sorted(set(folds)):
        tr, va = folds != f, folds == f
        Xtr, ytr, Xva = X[tr], y[tr], X[va]
        for k in kinds:
            Atr, Ava = encode(k, Xtr, Xva, scales)
            width_log.setdefault(k, []).append(Atr.shape[1])

            # 클래스 배수는 학습 부분 안의 내부 CV 에서만 고른다.
            inner = np.zeros((len(ytr), len(CLASSES)))
            skf = StratifiedKFold(n_splits=inner_splits, shuffle=True, random_state=SEED + f)
            for a, b in skf.split(Xtr, ytr):
                Ia, Ib = encode(k, Xtr[a], Xtr[b], scales)
                inner[b] = fit_logit(Ia, ytr[a], Ib)
            w = tune_class_weights(inner, ytr)
            pred[k][va] = decide(fit_logit(Atr, ytr, Ava), w)
    return {k: metrics(y, pred[k]) for k in kinds}, pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repeats', type=int, default=5)
    ap.add_argument('--inner-splits', type=int, default=3)
    ap.add_argument('--bootstrap', type=int, default=2000)
    ap.add_argument('--out', default='docs/CHJ-인코딩비교-결과.json')
    args = ap.parse_args()

    d = dbmod.load_dataset(missing_sentinel=MISSING)
    feats, X, y, db_folds = d['features'], d['X'], d['y'], d['folds']
    # ★ d['Xtest'] · d['ytest'] 는 이 파일 어디에서도 쓰지 않는다.

    sel = json.loads((ROOT / 'models' / 'selection_v1.json').read_text())['selected']
    Xs = X[:, [feats.index(f) for f in sel]]

    con = dbmod.connect(); cur = con.cursor()
    cur.execute('SELECT feature, var_scale FROM cb_feature_meta_v1 WHERE feature IN (%s)'
                % ','.join(['%s'] * len(sel)), sel)
    scale_of = dict(cur.fetchall()); con.close()
    scales = [scale_of[f] for f in sel]

    print(f'train {len(y)}건 · 7문항 · 고부담 {(y <= HIGH_BURDEN).mean():.3f}')
    for f, s in zip(sel, scales):
        n = len(np.unique(Xs[:, sel.index(f)]))
        miss = int((Xs[:, sel.index(f)] == MISSING).sum())
        print(f'  {f:34} {s:9} 수준 {n:2}  결측 {miss:4}')
    print(f'\n반복 {args.repeats}회 · 내부 {args.inner_splits}겹 · 부트스트랩 {args.bootstrap}회\n')

    kinds = list(LABELS)
    all_scores, keep_pred, width_log = [], None, {}
    for r in range(args.repeats):
        if r == 0:
            folds, how = db_folds, 'DB 고정 cv_fold'
        else:
            folds = np.zeros(len(y), dtype=int)
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED + r)
            for i, (_, va) in enumerate(skf.split(Xs, y), start=1):
                folds[va] = i
            how = f'층화 5-fold (seed {SEED + r})'
        t0 = time.time()
        scores, pred = run_repeat(Xs, y, folds, scales, kinds, args.inner_splits, width_log)
        print(f'반복 {r + 1}/{args.repeats} — {how} ({time.time() - t0:.0f}s)  '
              + ' · '.join(f'{k}={scores[k]["macro_f1"]:.4f}' for k in kinds), flush=True)
        all_scores.append({'repeat': r + 1, 'folds': how, 'scores': scores})
        if r == 0:
            keep_pred = pred

    widths = {k: int(round(float(np.mean(v)))) for k, v in width_log.items()}

    summary = {}
    for k in kinds:
        summary[k] = {'label': LABELS[k], 'design_columns': widths[k],
                      'n_params': widths[k] * len(CLASSES)}
        for m in METRIC_KEYS:
            vals = [s['scores'][k][m] for s in all_scores]
            summary[k][m] = {'mean': round(float(np.mean(vals)), 4),
                             'sd': round(float(np.std(vals, ddof=1)), 4) if len(vals) > 1 else None,
                             'per_repeat': [round(v, 4) for v in vals]}

    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, len(y), size=(args.bootstrap, len(y)))
    comparisons = []
    for k in kinds:
        if k == BASELINE:
            continue
        boot = bootstrap_diffs(y, keep_pred[k], keep_pred[BASELINE], boot_idx)
        entry = {'encoding': k, 'label': LABELS[k], 'vs': LABELS[BASELINE], 'metrics': {}}
        for m in METRIC_KEYS:
            diffs = [s['scores'][k][m] - s['scores'][BASELINE][m] for s in all_scores]
            mean, lo, hi = t_interval(diffs)
            bm, blo, bhi = boot[m]
            entry['metrics'][m] = {
                'repeat_mean_diff': round(mean, 4),
                'repeat_ci95': [round(lo, 4), round(hi, 4)] if lo is not None else None,
                'repeat_verdict': verdict(lo, hi),
                'boot_mean_diff': round(bm, 4),
                'boot_ci95': [round(blo, 4), round(bhi, 4)],
                'boot_verdict': verdict(blo, bhi),
            }
        comparisons.append(entry)

    result = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'author': '최호준 (CHJ)',
        'question': '척도를 살린 인코딩이 배포본의 전면 one-hot 보다 나은가',
        'note': ('train 2,398건만 사용. test 602건 미사용. 모델은 다항 로지스틱 하나로 고정하고 '
                 '인코딩만 바꿨다. 클래스 배수는 fold 학습 부분의 내부 CV 에서만 학습했다.'),
        'setup': {'n_train': int(len(y)), 'question_set': 'qs-v1.0.0',
                  'features': sel, 'var_scale': dict(zip(sel, scales)),
                  'rare_min': RARE_MIN, 'repeats': args.repeats,
                  'inner_splits': args.inner_splits, 'bootstrap': args.bootstrap,
                  'baseline': BASELINE},
        'summary': summary, 'comparisons': comparisons, 'per_repeat': all_scores,
    }
    out = ROOT / args.out
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    print('\n' + '=' * 80)
    print(f"{'인코딩':30} {'열':>4} {'모수':>5} {'macroF1':>9} {'고부담재현':>10} {'고부담F1':>9}")
    for k in kinds:
        s = summary[k]
        mark = ' ←기준' if k == BASELINE else ''
        print(f"{LABELS[k]:30} {s['design_columns']:4} {s['n_params']:5} "
              f"{s['macro_f1']['mean']:9.4f} {s['hb_recall']['mean']:10.4f} "
              f"{s['hb_f1']['mean']:9.4f}{mark}")
    print('\n' + '=' * 80)
    for m, title in (('macro_f1', 'macro F1'), ('hb_f1', '고부담 F1'), ('hb_recall', '고부담 재현율')):
        print(f'\n{LABELS[BASELINE]} 대비 — {title}')
        for c in comparisons:
            v = c['metrics'][m]
            ci, bci = v['repeat_ci95'], v['boot_ci95']
            print(f"  {c['label']:26} {v['repeat_mean_diff']:+.4f} "
                  f"[{ci[0]:+.4f},{ci[1]:+.4f}] {v['repeat_verdict']:14} | "
                  f"부트 {v['boot_mean_diff']:+.4f} [{bci[0]:+.4f},{bci[1]:+.4f}] {v['boot_verdict']}")
    print(f'\n저장: {out}')


if __name__ == '__main__':
    main()
