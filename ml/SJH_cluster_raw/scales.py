# -*- coding: utf-8 -*-
"""컬럼의 척도를 데이터에서 추정한다.

코드북 PDF 를 기계로 읽을 도구가 없어서 쓰는 대체 수단이다. 판정 규칙을 단순하고
설명 가능하게 두고, **애매하면 nominal 로 보수적으로** 간다 — 순서가 아닌 것을
순서로 다루면 거리가 왜곡되지만, 순서를 nominal 로 다루면 정보를 조금 잃을 뿐이다.

판정 결과는 문서에 표로 남겨 사람이 검토한다.
"""

CONTINUOUS_MIN_LEVELS = 15


def _blank(v):
    return v is None or str(v).strip() == ''


def judge(name, values):
    """한 컬럼의 척도를 'binary' / 'ordinal' / 'nominal' / 'continuous' 로 판정한다."""
    answered = [str(v).strip() for v in values if not _blank(v)]
    if not answered:
        return 'nominal'

    try:
        nums = [float(v) for v in answered]
    except ValueError:
        return 'nominal'                      # 주관식·문자 코드

    levels = sorted(set(nums))
    if len(levels) <= 2:
        return 'binary'
    if len(levels) >= CONTINUOUS_MIN_LEVELS:
        return 'continuous'
    if any(v != int(v) for v in levels):
        return 'continuous'                   # 소수점이 있으면 연속형

    # 정수 코드가 구멍 없이 이어지면 순서 척도로 본다 (1,2,3,4,5).
    # 1,2,3,9 처럼 띄엄띄엄하면 '9=기타' 같은 코드일 가능성이 높으므로 nominal.
    ints = [int(v) for v in levels]
    if ints == list(range(ints[0], ints[0] + len(ints))):
        return 'ordinal'
    return 'nominal'


def judge_all(rows, columns):
    """{컬럼: 척도} 판정표를 만든다."""
    return {c: judge(c, [r.get(c) for r in rows]) for c in columns}
