# -*- coding: utf-8 -*-
"""학습 데이터 적재 (읽기 전용). v_cb_tree_v1 을 쓰고 결측은 센티널로 대체한다."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ml' / '.pylibs'))
import numpy as np                      # noqa: E402
import pymysql                          # noqa: E402


def _env():
    env = {}
    p = ROOT / '.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    for k in ('DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'):
        if os.environ.get(k):
            env[k] = os.environ[k]
    missing = [k for k in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME') if not env.get(k)]
    if missing:
        raise SystemExit(f'.env 에 {", ".join(missing)} 가 없습니다.')
    return env


def connect():
    e = _env()
    return pymysql.connect(host=e['DB_HOST'], port=int(e.get('DB_PORT', 3306)),
                           user=e['DB_USER'], password=e['DB_PASSWORD'],
                           database=e['DB_NAME'], charset=e.get('DB_CHARSET', 'utf8mb4'),
                           connect_timeout=20)


def load_dataset(missing_sentinel=-1):
    con = connect()
    cur = con.cursor()
    cur.execute('SELECT feature FROM cb_feature_meta_v1 ORDER BY feature')
    features = [r[0] for r in cur.fetchall()]

    cols = ', '.join(f'`{f}`' for f in features)
    cur.execute(f'SELECT split, cv_fold, care_burden, {cols} FROM v_cb_tree_v1 ORDER BY row_id')
    rows = cur.fetchall()
    con.close()

    Xtr, ytr, folds, Xte, yte = [], [], [], [], []
    for r in rows:
        split, fold, y = r[0], r[1], int(r[2])
        vals = [missing_sentinel if v is None else float(v) for v in r[3:]]
        if split == 'train':
            Xtr.append(vals); ytr.append(y); folds.append(int(fold))
        else:
            Xte.append(vals); yte.append(y)

    d = {'features': features,
         'X': np.asarray(Xtr, dtype=np.float64), 'y': np.asarray(ytr),
         'folds': np.asarray(folds),
         'Xtest': np.asarray(Xte, dtype=np.float64), 'ytest': np.asarray(yte)}

    # 무결성 검증 — research.md 0장 실측값과 어긋나면 즉시 실패 (T025)
    assert len(d['y']) == 2398, f"train 이 2,398이 아닙니다: {len(d['y'])}"
    assert len(d['ytest']) == 602, f"test 가 602가 아닙니다: {len(d['ytest'])}"
    assert len(features) == 38, f"설명변수가 38개가 아닙니다: {len(features)}"
    assert sorted(set(d['folds'])) == [1, 2, 3, 4, 5], 'cv_fold 가 1~5가 아닙니다'
    banned = {'caregiver_life_satisfaction', 'care_difficulty_top1', 'needed_care_service_type',
              'work_care_gap_hours', 'work_care_gap_exp', 'integrated_care_awareness'}
    leaked = banned & set(features)
    assert not leaked, f'FR-004b 로 배제된 변수가 입력에 있습니다: {leaked}'
    return d


def record_model_version(version, family, qset, f1, rec, und_rate, notes):
    con = connect(); cur = con.cursor()
    cur.execute('UPDATE cb_model_version_v1 SET deactivated_at = NOW() WHERE deactivated_at IS NULL')
    cur.execute("""INSERT INTO cb_model_version_v1
        (model_version, family, question_set_version, macro_f1, high_burden_recall,
         undecidable_rate, activated_at, deactivated_at, notes)
        VALUES (%s,%s,%s,%s,%s,%s,NOW(),NULL,%s)
        ON DUPLICATE KEY UPDATE family=VALUES(family), macro_f1=VALUES(macro_f1),
          high_burden_recall=VALUES(high_burden_recall), undecidable_rate=VALUES(undecidable_rate),
          activated_at=NOW(), deactivated_at=NULL, notes=VALUES(notes)""",
                (version, family, qset, round(f1, 4), round(rec, 4), round(und_rate, 4), notes))
    con.commit(); con.close()
