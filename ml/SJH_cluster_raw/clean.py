# -*- coding: utf-8 -*-
"""군집화에 쓸 컬럼을 고른다. 버리는 이유를 반드시 함께 돌려준다.

집합들이 서로 겹치므로(전부결측인 주관식 등) 판정 순서를 고정해 이유가
하나로 정해지게 한다.
"""

IDENTIFIERS = ('ID', 'ADDCODE')
WEIGHT = 'WT'
TARGET = 'I13'


def _blank(v):
    return v is None or str(v).strip() == ''


def select_columns(rows, min_respondents=100):
    """(남길 컬럼 목록, {버린 컬럼: 이유}) 를 돌려준다.

    min_respondents: 응답자가 이보다 적은 컬럼은 버린다. 거리 계산에 거의
    기여하지 못하면서 잡음만 넣는다.
    """
    cols = list(rows[0].keys()) if rows else []
    keep, reasons = [], {}

    for c in cols:
        vals = [r.get(c) for r in rows]
        answered = [v for v in vals if not _blank(v)]

        if c in IDENTIFIERS:
            reasons[c] = '식별자'
        elif c == WEIGHT:
            reasons[c] = '조사가중치'
        elif c == TARGET:
            reasons[c] = 'target'
        elif c.startswith('__'):
            reasons[c] = '조인메타'
        elif not answered:
            reasons[c] = '전부결측'
        elif c.endswith('_op'):
            reasons[c] = '주관식'
        elif len(answered) < min_respondents:
            # 응답자 수를 상수 검사보다 먼저 본다. 1명만 답한 컬럼은 자동으로
            # 상수가 되는데, '상수'라고 적으면 왜 버렸는지 오해를 부른다.
            reasons[c] = f'응답자 {len(answered)}명 < {min_respondents}'
        elif len(set(answered)) <= 1:
            reasons[c] = '상수'
        else:
            keep.append(c)

    return keep, reasons
