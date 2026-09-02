"""DB 어댑터 — **스냅샷 생성에만 쓴다.**

학습 단계도 추론 서비스도 이 모듈을 부르지 않는다. DB 는 바뀌고, 바뀌면 과거 모델을
재현할 수 없기 때문이다(설계 4.3). 학습은 고정된 스냅샷 파일만 읽는다.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_VIEW = 'v_cb_tree_v1'


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
    import pymysql
    e = _env()
    return pymysql.connect(host=e['DB_HOST'], port=int(e.get('DB_PORT', 3306)),
                           user=e['DB_USER'], password=e['DB_PASSWORD'],
                           database=e['DB_NAME'], charset=e.get('DB_CHARSET', 'utf8mb4'),
                           connect_timeout=20)


def fetch():
    """(features, rows, info) 를 돌려준다. rows 는 스냅샷에 그대로 쓸 dict 목록."""
    e = _env()
    con = connect()
    cur = con.cursor()
    cur.execute('SELECT feature FROM cb_feature_meta_v1 ORDER BY feature')
    features = [r[0] for r in cur.fetchall()]

    cols = ', '.join(f'`{f}`' for f in features)
    cur.execute(f'SELECT split, cv_fold, care_burden, {cols} '
                f'FROM {SOURCE_VIEW} ORDER BY row_id')
    rows = []
    for r in cur.fetchall():
        row = {'split': r[0], 'cv_fold': int(r[1] or 0), 'care_burden': int(r[2])}
        for f, v in zip(features, r[3:]):
            row[f] = -1 if v is None else float(v)      # 결측 센티널
        rows.append(row)
    con.close()
    # 원칙 III — 비밀번호는 넘기지 않는다
    return features, rows, {'source_view': SOURCE_VIEW,
                            'db': {'host': e['DB_HOST'], 'database': e['DB_NAME']}}
