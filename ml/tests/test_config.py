"""도메인 상수 — 헌법·스펙이 정한 값이라 실험으로 바꾸지 않는다."""
from cb_burden import config


def test_척도는_1이_최고부담인_역방향이다():
    assert config.CLASSES == [1, 2, 3, 4, 5]
    assert config.HIGH_BURDEN_LABELS == [1, 2]


def test_배제변수_6개가_그대로_있다():
    # FR-004b — target 과 같은 블록이라 입력에 쓰지 않는다
    assert len(config.EXCLUDED_FEATURES) == 6
    assert 'caregiver_life_satisfaction' in config.EXCLUDED_FEATURES


def test_성공기준이_스펙과_같다():
    sc = config.SUCCESS_CRITERIA
    assert sc['max_f1_loss'] == 0.03
    assert sc['max_recall_loss'] == 0.05
    assert sc['min_recall_abs'] == 0.70
    assert sc['max_undecidable_rate'] == 0.10


def test_시드가_원본_학습_스크립트와_같다():
    # 다르면 같은 데이터로도 다른 모델이 나온다. ml/train.py 의 SEED 와 맞춘다.
    assert config.SEED == 20260901


def test_임계값은_여기_없다():
    # 판정 임계값은 설정(cb_config_v1)이 소유한다. 코드에 못박지 않는다(FR-009c).
    assert not hasattr(config, 'TAU_CONF')
    assert not hasattr(config, 'TAU_DENS')
