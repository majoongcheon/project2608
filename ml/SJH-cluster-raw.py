# -*- coding: utf-8 -*-
"""원본 507컬럼 군집화 — A안 (읽기 전용 실험).

    PYTHONPATH=ml/.pylibs-sjh:ml/.pylibs:ml python3 ml/SJH-cluster-raw.py \
        --null-reps 20 --out docs/SJH-군집화-결과.json

하는 일 — 원본 CSV 에 기존 train/test 분할을 붙이고(test 는 열지 않는다),
분기 결측을 게이트 이진 변수로 승격시킨 뒤, Gower 거리로 PAM·계층군집을 돌리고,
열별 셔플 널 베이스라인과 비교해 구조 유무를 판정한다.

DB 는 조회만 하고 models/ 는 건드리지 않는다.
"""
import argparse
import json
import sys
from datetime import datetime

import numpy as np

from SJH_cluster_raw import clean, cluster, gates, gower, load, scales, score

# 누수 6변수의 원본 컬럼 (docs/2024csv_column_mapping.xlsx 대조, FR-004b)
LEAK_COLUMNS = {
    'I14':   'caregiver_life_satisfaction',
    'I10':   'care_difficulty_top1',
    'I12_1': 'needed_care_service_type',
    'I11_H': 'work_care_gap_hours',
    'I11':   'work_care_gap_exp',
    'I12':   'integrated_care_awareness',
}
K_RANGE = range(2, 11)
SEED = 20260902


def build_matrix(rows, keep, found_gates):
    """(X, kinds, 컬럼이름) 을 만든다.

    A안의 입력 = 전원응답 컬럼 + 게이트 이진 변수.
    게이트는 나머지 컬럼의 '존재 여부'를 압축한 것이라, 내용을 안 써도
    507컬럼의 구조 정보가 반영된다.
    """
    full = [c for c in keep if all(str(r.get(c, '')).strip() != '' for r in rows)]
    kinds_map = scales.judge_all(rows, full)

    names, kinds, cols = [], [], []
    for c in full:
        if kinds_map[c] in ('ordinal', 'continuous'):
            col = [float(str(r[c]).strip()) for r in rows]
        else:
            levels = {v: i for i, v in enumerate(sorted({str(r[c]).strip() for r in rows}))}
            col = [float(levels[str(r[c]).strip()]) for r in rows]
        names.append(c)
        kinds.append(kinds_map[c])
        cols.append(col)

    for i, g in enumerate(found_gates):
        names.append(f'__gate{i}')
        kinds.append('binary')
        cols.append([float(v) for v in g['values']])

    return np.array(cols, dtype=np.float64).T, kinds, names


def run_once(X, kinds, weights, y, gate_rows, null_reps, rng):
    """한 조건(누수 포함 또는 제외)을 끝까지 돌린다."""
    D = gower.distance(X, kinds, weights)
    rows = []
    for k in K_RANGE:
        for name, labels in (('pam', cluster.pam(D, k, seed=SEED)),
                             ('hier', cluster.hierarchical(D, k))):
            rec = {'k': k, 'method': name,
                   'silhouette': score.silhouette(D, labels),
                   'gate_contamination': score.gate_contamination(labels, gate_rows)}
            rec.update(score.agreement(labels, y))
            rec['lift'] = score.high_burden_lift(labels, y)
            rec['crosstab'] = score.crosstab(labels, y)
            rec['min_cluster_size'] = min(v['n'] for v in rec['lift'].values())
            rec['degenerate'] = rec['min_cluster_size'] < 0.01 * len(y)
            rows.append(rec)

    # 퇴화 분할(한 군집이 전체의 1% 미만)은 후보에서 뺀다. average linkage 는
    # 이상치 몇 명을 떼어내고 실루엣만 높게 만드는 일이 잦다 — 실측에서
    # 계층군집 k=2 가 4 대 2,394 로 갈리며 실루엣 0.18 을 냈으나 ARI 는 0.0001 이었다.
    usable = [r for r in rows if not r['degenerate']]
    if not usable:
        raise RuntimeError('모든 구성이 퇴화 분할이다')
    best = max(usable, key=lambda r: r['silhouette'])

    nulls = []
    for i in range(null_reps):
        Xs = X.copy()
        for c in range(Xs.shape[1]):
            Xs[:, c] = rng.permutation(Xs[:, c])
        Dn = gower.distance(Xs, kinds, weights)
        nulls.append(score.silhouette(Dn, cluster.pam(Dn, best['k'], seed=SEED)))
        print(f'  널 {i + 1}/{null_reps} 실루엣 {nulls[-1]:.4f}', file=sys.stderr)

    return {'rows': rows, 'best': best,
            'null': score.null_verdict(best['silhouette'], nulls)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--null-reps', type=int, default=20)
    ap.add_argument('--out', default='docs/SJH-군집화-결과.json')
    ap.add_argument('--csv', default='data/snapshots/2024.csv')
    ap.add_argument('--mapping', default='docs/학습데이터셋-컬럼정의.md')
    args = ap.parse_args()

    raw = load.read_raw(args.csv)
    mapping = load.read_mapping(args.mapping)
    joined = load.join_split(raw, load.load_db_rows(), mapping)

    train = [r for r in joined if r['__split'] == 'train']
    print(f'train {len(train)}건 (test 는 열지 않는다)', file=sys.stderr)
    y = np.array([int(r['I13']) for r in train])

    result = {'generated_at': datetime.now().isoformat(timespec='seconds'),
              'n_train': len(train), 'seed': SEED, 'null_reps': args.null_reps,
              'conditions': {}}
    rng = np.random.default_rng(SEED)

    for label, drop_leak in (('누수 포함', False), ('누수 제외', True)):
        keep, reasons = clean.select_columns(train, min_respondents=100)
        if drop_leak:
            keep = [c for c in keep if c not in LEAK_COLUMNS]
        found = gates.find_gates(train, keep, min_columns=2)
        X, kinds, names = build_matrix(train, keep, found)

        # A안은 블록마다 게이트 변수가 이미 하나뿐이라 중복 계수가 없다.
        # 그래서 가중치는 전부 1.0 이다. gower.block_weights 는 게이트 아래
        # 문항의 '내용'까지 넣는 B안에서 쓰인다.
        weights = [1.0] * len(names)
        print(f'[{label}] 컬럼 {len(names)} · 게이트 {len(found)}', file=sys.stderr)

        out = run_once(X, kinds, weights, y, gates.gate_matrix(found), args.null_reps, rng)
        out['n_columns'] = len(names)
        out['n_gates'] = len(found)
        out['gates'] = [{'columns': g['columns'], 'n_answered': g['n_answered']}
                        for g in found]
        out['dropped'] = dict(sorted(reasons.items()))
        out['scales'] = dict(zip(names, kinds))
        result['conditions'][label] = out

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n저장: {args.out}', file=sys.stderr)

    for label, c in result['conditions'].items():
        v = c['null']
        print(f'[{label}] 최고 k={c["best"]["k"]} 실루엣 {v["observed"]:.4f} · '
              f'널 평균 {v["null_mean"]:.4f} · p={v["p_value"]:.3f} · '
              f'구조 {"있음" if v["structured"] else "없음"}', file=sys.stderr)


if __name__ == '__main__':
    main()
