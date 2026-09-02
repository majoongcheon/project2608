# -*- coding: utf-8 -*-
"""원본 조사 CSV 를 읽고 기존 train/test 분할을 붙인다.

`cb_dataset_v1.row_key` 는 행 내용 MD5 라 원본 CSV 의 `ID` 와 대응하지 않는다.
그래서 38변수 + target 의 **값 튜플**로 조인한다. 값이 중복되거나 매칭이 실패하면
조용히 틀린 분할을 쓰는 대신 멈춘다 — 분할이 틀리면 test 봉인이 깨진다.
"""
import csv
import os
import re


class JoinError(RuntimeError):
    """조인이 유일하지 않을 때. 조용히 넘기면 test 가 오염된다."""


# 원본의 무응답 코드 → DB 에서는 NULL. `docs/학습데이터셋-컬럼정의.md` §② 의 실측 결과다.
# 설문지 PDF 를 대조해 정한 것이라 코드값만 보고 일괄 처리하면 안 된다 —
# `secondary_caregiver_type` 의 9 는 "9. 없음"이라는 유효한 보기이고 518건이다.
SENTINELS = {
    'age_disability_suspected': {'999'},        # A6  나이 문항의 무응답 30건
    'has_chronic_disease': {'99'},              # G2  유효 코드가 0~17
    'family_support_for_employment': {'9'},     # F5  척도 1~5
    'school_helpfulness': {'9'},                # B4  척도 1~5
    'daily_routine_satisfaction': {'9'},        # G8  척도 1~5
    'wanted_to_stay_at_last_job': {'9'},        # E5  척도 1~2
}


def read_raw(path):
    """원본 CSV 를 dict 리스트로 읽는다. 값은 문자열 그대로 둔다."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def read_mapping(md_path):
    """`학습데이터셋-컬럼정의.md` 에서 {영문컬럼: 원문항} 을 뽑는다.

    표 형식: | `feature` | 한글라벨 | G6 | ...
    """
    pat = re.compile(r'^\| `([a-z_]+)` \| *([^|]+?) *\| *([A-Za-z0-9_]+) *\|', re.M)
    with open(md_path, encoding='utf-8') as f:
        found = {a: c for a, _, c in pat.findall(f.read())}
    found.pop('care_burden', None)
    return found


def _norm(value, sentinels=()):
    """빈 문자열과 무응답 코드를 None 으로 통일한다."""
    if value is None:
        return None
    v = str(value).strip()
    if v == '' or v in sentinels:
        return None
    return v


def _key(values, sentinel_sets=None):
    """조인 키. None·빈 문자열·무응답 코드를 하나로 통일한다."""
    if sentinel_sets is None:
        sentinel_sets = [()] * len(values)
    return tuple(_norm(v, s) for v, s in zip(values, sentinel_sets))


def join_split(raw_rows, db_rows, mapping):
    """raw 각 행에 `__split`·`__cv_fold` 를 붙여 새 dict 리스트를 돌려준다.

    mapping: {영문컬럼: 원문항}. target 은 care_burden ↔ I13 으로 고정.
    """
    feats = sorted(mapping)
    if db_rows:
        missing = [f for f in feats if f not in db_rows[0]]
        if missing:
            raise JoinError(f'DB 에 없는 컬럼이 매핑에 있다: {missing}')

    # DB 는 이미 정규화된 값이므로 센티널을 적용하지 않는다. 원본에만 적용한다.
    sets = [SENTINELS.get(f, ()) for f in feats] + [()]

    index = {}
    for r in db_rows:
        k = _key([r[f] for f in feats] + [r['care_burden']])
        if k in index:
            raise JoinError(f'DB 쪽에 값 튜플이 중복된다: {k}')
        index[k] = r

    seen = len({_key([r[mapping[f]] for f in feats] + [r['I13']], sets) for r in raw_rows})
    if seen != len(raw_rows):
        raise JoinError(f'원본 쪽 값 튜플이 중복된다 ({seen} != {len(raw_rows)})')

    out = []
    for row in raw_rows:
        k = _key([row[mapping[f]] for f in feats] + [row['I13']], sets)
        hit = index.get(k)
        if hit is None:
            raise JoinError(f'매칭되는 DB 행이 없다 (ID={row.get("ID")}): {k}')
        merged = dict(row)
        merged['__split'] = hit['split']
        merged['__cv_fold'] = hit['cv_fold']
        out.append(merged)
    return out


def load_db_rows():
    """`cb_dataset_v1` 을 읽기 전용으로 조회한다. 쓰기는 하지 않는다."""
    import pymysql
    for line in open('.env', encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('\'"'))
    con = pymysql.connect(
        host=os.environ['DB_HOST'], port=int(os.environ['DB_PORT']),
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME'], charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor)
    try:
        with con.cursor() as cur:
            cur.execute('SELECT * FROM cb_dataset_v1')
            return cur.fetchall()
    finally:
        con.close()
