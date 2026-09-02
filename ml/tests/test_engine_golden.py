"""추론 엔진 — 배포본과 같은 답을 내는가. parity 테스트가 하던 역할을 잇는다."""
import json
from pathlib import Path

import numpy as np
import pytest
from cb_burden.serve import engine

RELEASE = Path('models')
# 승격된 릴리스는 golden_v1.json 을 갖는다. 현재 배포본(v1.0.0)은 이관 전에 만들어져
# parity_v1.json 만 있으므로 둘 다 받는다.
GOLDEN = (RELEASE / 'golden_v1.json') if (RELEASE / 'golden_v1.json').exists() \
    else (RELEASE / 'parity_v1.json')

DECIDED_ROW = [4, 4, 5, 1, -1, 3, 1]        # 배포본 기준 판정 성립 (max 0.4295, rarity -1.1383)
WEIGHTS = [1.1, 1.1, 1.0, 1.0, 1.0]


@pytest.fixture(scope='module')
def eng():
    return engine.Engine.load(RELEASE)


def test_확률이_골든과_1e_9_이내로_같다(eng):
    fx = json.loads(GOLDEN.read_text(encoding='utf-8'))
    worst = 0.0
    for c in fx['cases']:
        p = eng.proba(c['input'])
        worst = max(worst, float(np.abs(np.array(p) - np.array(c['proba'])).max()))
    assert worst < 1e-9, f'최대 오차 {worst:.3e}'


def test_판정_성립_사례가_판정된다(eng):
    got = eng.decide(DECIDED_ROW, tau_conf=0.3239, tau_dens=-2.4343,
                     decision_weights=WEIGHTS, contrib_threshold=0.1325)
    assert got['decided'] is True
    assert got['internalLabel'] in (1, 2, 3, 4, 5)
    assert got['undecidableReason'] is None
    assert got['contributions'] and len(got['contributions']) == 3


def test_확신도_기준을_올리면_ambiguous_다(eng):
    got = eng.decide(DECIDED_ROW, tau_conf=0.9, tau_dens=-99.0,
                     decision_weights=WEIGHTS, contrib_threshold=0.1325)
    assert got['decided'] is False
    assert got['undecidableReason'] == 'ambiguous'


def test_희소성_기준만_올려도_판정_불가다(eng):
    # 확신도는 통과하는데 희소성만 걸리는 경우 — 두 조건이 독립인지 확인한다
    got = eng.decide(DECIDED_ROW, tau_conf=0.0, tau_dens=-1.0,
                     decision_weights=WEIGHTS, contrib_threshold=0.1325)
    assert got['decided'] is False
    assert got['undecidableReason'] == 'sparse'


def test_두_조건이_함께_걸리면_sparse_가_우선한다(eng):
    got = eng.decide(DECIDED_ROW, tau_conf=0.9, tau_dens=-1.0,
                     decision_weights=WEIGHTS, contrib_threshold=0.1325)
    assert got['undecidableReason'] == 'sparse'


def test_판정_불가면_구간과_기여요인을_내지_않는다(eng):
    got = eng.decide(DECIDED_ROW, tau_conf=0.9, tau_dens=-99.0,
                     decision_weights=WEIGHTS, contrib_threshold=0.1325)
    assert got['internalLabel'] is None          # FR-009a
    assert got['contributions'] is None          # FR-011c


def test_결정_가중치가_실제로_적용된다(eng):
    # 가산점을 빼면 다른 구간이 나올 수 있다. 정책이 계산에 반영되는지 본다.
    a = eng.decide(DECIDED_ROW, 0.0, -99.0, [1, 1, 1, 1, 1], 0.1325)
    b = eng.decide(DECIDED_ROW, 0.0, -99.0, [9, 9, 1, 1, 1], 0.1325)
    assert b['internalLabel'] <= a['internalLabel']   # 1·2 쪽으로 밀린다


def test_버전을_함께_낸다(eng):
    got = eng.decide(DECIDED_ROW, 0.3239, -2.4343, WEIGHTS, 0.1325)
    assert got['modelVersion'] == 'v1.0.0'
    assert got['questionSetVersion'] == 'qs-v1.0.0'


def test_기여요인은_실제로_판정된_구간_기준이다(eng):
    """정책 가중치로 구간이 바뀌면 기여도도 그 구간 기준이어야 한다.

    saabas.contributions 는 cls 를 주지 않으면 **아티팩트의 결정 가중치**로 구간을 다시
    고른다. 정책 값으로 다른 구간이 나왔는데 기여도만 옛 구간 기준이면, 화면의 설명이
    표시된 구간과 어긋난다.
    """
    from cb_burden.explain.saabas import contributions as raw

    strong = eng.decide(DECIDED_ROW, 0.0, -99.0, [9, 9, 1, 1, 1], 0.1325)
    idx = eng.classes.index(strong['internalLabel'])
    expected, _ = raw(eng.model_json, list(map(float, DECIDED_ROW)), idx)

    got = {c['feature']: c['contrib'] for c in strong['contributions']}
    for j, f in enumerate(eng.features):
        if f in got:
            assert abs(got[f] - round(float(expected[j]), 6)) < 1e-9, (
                f'{f}: 기여도가 판정된 구간({strong["internalLabel"]}) 기준이 아니다')
