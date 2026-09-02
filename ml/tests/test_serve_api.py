"""추론 서비스 계약 — 잘못된 입력을 경계에서 막는다."""
import pytest
from fastapi.testclient import TestClient

from cb_burden.serve.app import create_app

POLICY = {'tauConf': 0.3239, 'tauDens': -2.4343,
          'decisionWeights': [1.1, 1.1, 1.0, 1.0, 1.0],
          'contributionMinThreshold': 0.1325}


@pytest.fixture(scope='module')
def client():
    return TestClient(create_app('models'))


def _answers():
    vals = [4, 4, 5, 1, None, 3, 1]
    return [{'questionNo': i + 1, 'value': v} for i, v in enumerate(vals)]


def test_health_가_버전과_가중치를_알려준다(client):
    b = client.get('/health').json()
    assert b['status'] == 'ok'
    assert b['modelVersion'] == 'v1.0.0'
    assert b['questionSetVersion'] == 'qs-v1.0.0'
    # 설정과 아티팩트가 갈라지는지 백엔드가 대조할 수 있어야 한다
    assert len(b['artifactDecisionWeights']) == 5


def test_정상_요청은_판정을_돌려준다(client):
    r = client.post('/predict', json={'answers': _answers(), 'policy': POLICY})
    assert r.status_code == 200
    b = r.json()
    assert len(b['proba']) == 5
    assert b['decided'] is True
    assert b['internalLabel'] in (1, 2, 3, 4, 5)
    assert len(b['contributions']) == 3


def test_policy_가_없으면_거절한다(client):
    # 기본값을 두면 조용히 다른 기준으로 판정하게 된다
    r = client.post('/predict', json={'answers': _answers()})
    assert r.status_code == 422


def test_임계값이_범위_밖이면_거절한다(client):
    bad = dict(POLICY, tauConf=1.5)
    assert client.post('/predict', json={'answers': _answers(), 'policy': bad}).status_code == 422
    bad = dict(POLICY, tauDens=0.5)
    assert client.post('/predict', json={'answers': _answers(), 'policy': bad}).status_code == 422


def test_가중치_길이가_다르면_거절한다(client):
    bad = dict(POLICY, decisionWeights=[1.0, 1.0])
    assert client.post('/predict', json={'answers': _answers(), 'policy': bad}).status_code == 422


def test_문항_수가_다르면_거절한다(client):
    r = client.post('/predict', json={'answers': _answers()[:3], 'policy': POLICY})
    assert r.status_code == 422


def test_모르는_문항번호는_거절한다(client):
    a = _answers()
    a[0]['questionNo'] = 99
    r = client.post('/predict', json={'answers': a, 'policy': POLICY})
    assert r.status_code == 422


def test_해당사항_없음은_결측_센티널로_들어간다(client):
    a = _answers()
    b1 = client.post('/predict', json={'answers': a, 'policy': POLICY}).json()
    a2 = [dict(x) for x in a]
    a2[4]['value'] = -1                       # null 과 같은 뜻
    b2 = client.post('/predict', json={'answers': a2, 'policy': POLICY}).json()
    assert b1['proba'] == b2['proba']


def test_응답에_개인정보가_없다(client):
    b = client.post('/predict', json={'answers': _answers(), 'policy': POLICY}).json()
    assert set(b) == {'modelVersion', 'questionSetVersion', 'proba', 'decided',
                      'internalLabel', 'maxProba', 'rarity', 'undecidableReason',
                      'contributions'}
