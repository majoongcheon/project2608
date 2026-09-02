"""도메인 상수.

여기 있는 값은 헌법(.specify/memory/constitution.md)과 스펙이 정한 것이다.
실험 결과로 바꾸지 않는다. 바꾸려면 스펙을 먼저 고친다.
"""

# 내부 라벨. 1 이 최고부담인 역방향 척도다 — 임계값 비교가 <= 인 이유.
CLASSES = [1, 2, 3, 4, 5]
HIGH_BURDEN_LABELS = [1, 2]

MISSING_SENTINEL = -1
TARGET = 'care_burden'

# FR-004b — target(I13) 과 같은 블록의 6변수. 입력·문항 어디에도 쓰지 않는다.
EXCLUDED_FEATURES = frozenset({
    'caregiver_life_satisfaction', 'care_difficulty_top1', 'needed_care_service_type',
    'work_care_gap_hours', 'work_care_gap_exp', 'integrated_care_awareness',
})

# SC-004 · SC-005 · SC-016
SUCCESS_CRITERIA = {
    'max_f1_loss': 0.03,
    'max_recall_loss': 0.05,
    'min_recall_abs': 0.70,
    'max_undecidable_rate': 0.10,
}

# ★ 원본 ml/train.py 와 같아야 한다. 다르면 다른 모델이 나온다.
SEED = 20260901

# 선별 정지 조건의 여유값 — CV 에서 하한+마진을 확보해 test 변동을 흡수한다
REC_MARGIN = 0.03
F1_MARGIN = 0.01

# 데이터 실측 (2026-09-01 확인). integrity 검증에 쓴다.
EXPECTED_ROWS = 3000
EXPECTED_TRAIN = 2398
EXPECTED_TEST = 602
EXPECTED_FEATURES = 38
EXPECTED_FOLDS = [1, 2, 3, 4, 5]
