# -*- coding: utf-8 -*-
"""연속형 나이 변수의 구간화.

원-핫 인코딩에서 나이를 한 살 단위로 두면 `caregiver_age` 78열, `age_disability_suspected`
60열이 되어 전체 224열의 62%를 차지한다. 두 가지 문제가 생긴다.

  1. 희소성 — 특정 나이의 학습 데이터 내 빈도가 1~2%라 rarity 가 크게 내려가고,
     FR-009a 의 판정 불가가 이 두 변수 때문에 발동한다 (실측: 희소성 발동 24건 전부).
  2. 순서 정보 상실 — 선형 모델에서 57세와 58세가 완전히 무관한 별개 범주가 된다.

구간 경계는 train 분포에서 각 구간이 최소 3% 이상을 갖도록 잡았다.
**학습과 화면이 같은 정의를 쓴다** — 이 파일 하나만 고치면 양쪽이 함께 바뀐다.
"""

# feature: [(코드, 라벨, 하한, 상한)]  — 상한 포함
AGE_BINS = {
    'caregiver_age': [
        (1, '39세 이하',   0, 39),
        (2, '40~49세',    40, 49),
        (3, '50~54세',    50, 54),
        (4, '55~59세',    55, 59),
        (5, '60~64세',    60, 64),
        (6, '65~69세',    65, 69),
        (7, '70~79세',    70, 79),
        (8, '80세 이상',   80, 200),
    ],
    'age_disability_suspected': [
        (1, '만 2세 이전',   0, 2),
        (2, '만 3~5세',     3, 5),
        (3, '만 6~9세',     6, 9),
        (4, '만 10~14세',  10, 14),
        (5, '만 15세 이후', 15, 200),
    ],
}


def to_bin(feature: str, value):
    """원래 나이 값을 구간 코드로. 결측(-1 이하)은 그대로 둔다."""
    if feature not in AGE_BINS or value is None or value < 0:
        return value
    for code, _, lo, hi in AGE_BINS[feature]:
        if lo <= value <= hi:
            return code
    return value


def options(feature: str):
    """화면 선택지. 코드와 라벨이 학습과 같은 정의에서 나온다."""
    return [(code, label) for code, label, _, _ in AGE_BINS[feature]]
