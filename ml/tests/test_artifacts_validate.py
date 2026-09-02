"""아티팩트 검증 — 배포 전 마지막 관문. 백엔드 기동 검사와 같은 규칙을 갖는다."""
import pytest
from cb_burden.artifacts import validate


def _bundle():
    return {
        'model': {
            'model_version': 'v1.0.0', 'question_set_version': 'qs-v1.0.0',
            'family': 'logit', 'features': ['a', 'b'], 'classes': [1, 2, 3, 4, 5],
            'decision_weights': [1.1, 1.1, 1.0, 1.0, 1.0], 'missing_sentinel': -1,
            'categories': [[-1, 1], [1, 2]], 'spans': [[0, 2], [2, 2]],
            'coef': [[0.0] * 4 for _ in range(5)], 'intercept': [0.0] * 5,
            'expected_contrib': [[0.0] * 5 for _ in range(2)],
        },
        'selection': {'model_version': 'v1.0.0', 'selected': ['a', 'b']},
        'uncertainty': {'model_version': 'v1.0.0', 'tau_conf': 0.32,
                        'tau_dens': -2.43, 'freq_table': {'a': {'1': 0.5}}},
        'questions': {'question_set_version': 'qs-v1.0.0',
                      'questions': [{'feature': 'a'}, {'feature': 'b'}]},
        'contribution': {'min_threshold': 0.13},
    }


def test_정상_아티팩트는_통과한다():
    assert validate.check(_bundle()) is True


def test_features_순서가_선별결과와_다르면_거부한다():
    b = _bundle()
    b['selection']['selected'] = ['b', 'a']
    with pytest.raises(ValueError, match='selection'):
        validate.check(b)


def test_문항_순서가_모델과_다르면_거부한다():
    b = _bundle()
    b['questions']['questions'] = [{'feature': 'b'}, {'feature': 'a'}]
    with pytest.raises(ValueError, match='questions'):
        validate.check(b)


def test_척도가_뒤집히면_거부한다():
    # 이 프로젝트에서 가장 실수하기 쉬운 지점이다
    b = _bundle()
    b['model']['classes'] = [5, 4, 3, 2, 1]
    with pytest.raises(ValueError, match='척도'):
        validate.check(b)


def test_확신도_임계값이_범위_밖이면_거부한다():
    b = _bundle()
    b['uncertainty']['tau_conf'] = 1.5
    with pytest.raises(ValueError, match='tau_conf'):
        validate.check(b)


def test_희소성_임계값이_양수면_거부한다():
    b = _bundle()
    b['uncertainty']['tau_dens'] = 0.5
    with pytest.raises(ValueError, match='tau_dens'):
        validate.check(b)


def test_필수_키가_없으면_거부한다():
    b = _bundle()
    del b['model']['decision_weights']
    with pytest.raises(ValueError, match='decision_weights'):
        validate.check(b)


def test_지원하지_않는_계열이면_거부한다():
    b = _bundle()
    b['model']['family'] = 'xgboost'
    with pytest.raises(ValueError, match='계열'):
        validate.check(b)


def test_가중치_길이가_다르면_거부한다():
    b = _bundle()
    b['model']['decision_weights'] = [1.0, 1.0]
    with pytest.raises(ValueError, match='decision_weights'):
        validate.check(b)


def test_모델_버전이_아티팩트마다_다르면_거부한다():
    b = _bundle()
    b['uncertainty']['model_version'] = 'v9.9.9'
    with pytest.raises(ValueError, match='모델 버전'):
        validate.check(b)
