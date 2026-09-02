"""정규화 손잡이 — 값을 넣을 수 있게 하되 **기본값은 지금과 똑같아야** 한다.

기본값이 달라지면 배포 중인 모델과 다른 것이 만들어진다. 그것부터 막는다.
"""
import pytest
from sklearn.linear_model import LogisticRegression

from cb_burden import config
from cb_burden.stages import _core


def test_기본값은_지금_배포본과_같다():
    m = _core.make_logit()
    assert isinstance(m, LogisticRegression)
    assert m.penalty == 'l2'          # sklearn 기본값
    assert m.C == 1.0                 # sklearn 기본값
    assert m.max_iter == 2000         # 지금 코드가 주던 값
    assert m.random_state == config.SEED
    assert m.solver == 'lbfgs'        # sklearn 기본값


def test_정규화_세기를_바꿀_수_있다():
    m = _core.make_logit(C=0.05)
    assert m.C == 0.05
    assert m.penalty == 'l2'          # 나머지는 그대로


def test_L1_은_solver_를_알아서_바꾼다():
    # lbfgs 는 L1 을 못 푼다. saga 로 바꿔주지 않으면 sklearn 이 오류를 낸다.
    m = _core.make_logit(penalty='l1')
    assert m.penalty == 'l1'
    assert m.solver == 'saga'


def test_elasticnet_도_받는다():
    m = _core.make_logit(penalty='elasticnet', l1_ratio=0.5)
    assert m.penalty == 'elasticnet'
    assert m.solver == 'saga'
    assert m.l1_ratio == 0.5


def test_None_을_주면_기본값을_쓴다():
    # 호출부에서 params=None 을 그대로 넘겨도 지금 동작이 유지돼야 한다
    m = _core.make_logit(C=None, penalty=None)
    assert m.C == 1.0 and m.penalty == 'l2'
